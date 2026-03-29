Keep a Changelog に準拠した変更履歴 (日本語)
==========================================

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に従います。

Unreleased
----------
（現在未リリースの変更はありません）

[0.1.0] - 2026-03-29
-------------------

Added
- パッケージ初期リリース (kabusys v0.1.0)
  - パッケージメタ情報
    - src/kabusys/__init__.py にてバージョンを "0.1.0" として公開。
    - パッケージ外部公開モジュール: data, strategy, execution, monitoring を __all__ で定義。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルートを .git または pyproject.toml から検出して .env / .env.local を読み込む。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
    - OS 環境変数を保護する protected オプションを使って .env.local による上書きを制御。
  - .env 行パーサ実装:
    - コメント、export プレフィックス、クォート（シングル／ダブル）内のエスケープ、インラインコメントの取り扱い等に対応。
  - Settings クラスを提供（settings インスタンスをエクスポート）:
    - 必須設定取得用の _require による未設定時の ValueError。
    - J-Quants / kabuステーション / Slack / データベースパスなどのプロパティを定義。
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL のバリデーション。
    - duckdb/sqlite のデフォルトパス設定とユーティリティプロパティ（is_live / is_paper / is_dev）。

- AI モジュール (src/kabusys/ai)
  - ニュースNLP スコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI (gpt-4o-mini) を用いて銘柄ごとのセンチメント ai_score を生成。
    - スコア生成ウィンドウは JST 基準（前日 15:00 〜 当日 08:30）を UTC に変換して使用する calc_news_window を提供。
    - バッチサイズ、1銘柄あたり記事上限、文字数トリムなどトークン過膨張対策を実装（_BATCH_SIZE, _MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - API 呼び出しのリトライ（429/ネットワーク断/タイムアウト/5xx）、指数的バックオフ、失敗時のフォールバック（スキップして継続）。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results リスト検証、コード整形、数値チェック、±1.0 でクリップ）。
    - DuckDB への書き込みは部分失敗を許容する設計（該当コードのみ DELETE → INSERT）で idempotent。
    - テスト容易性のため _call_openai_api を patch 可能。
    - パブリック API: score_news(conn, target_date, api_key=None) を提供。
    - __all__ で score_news をエクスポート (src/kabusys/ai/__init__.py)。
  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
    - prices_daily / raw_news を参照し、calc_news_window によりニュースウィンドウを決定、OpenAI (gpt-4o-mini) を用いて macro_sentiment を算出。
    - API 障害時は macro_sentiment=0.0 として継続（フェイルセーフ）。一定回数のリトライを実装。
    - 計算結果は market_regime テーブルへ冪等に書き込む（BEGIN/DELETE/INSERT/COMMIT）。書き込み失敗時は ROLLBACK を試行して例外を再送出。
    - テスト容易性のため内部の API 呼び出しを差し替え可能に設計。

- Data / ETL / カレンダー関連 (src/kabusys/data)
  - ETL パイプライン基盤 (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult データクラスを定義し（ターゲット日、取得数、保存数、品質問題リスト、エラー一覧等）、to_dict により監査用辞書へ変換可能。
    - 差分取得・バックフィル（デフォルト backfill 3日）、品質チェックの統合を想定した設計。
    - DuckDB のテーブル存在チェック、最大日付取得ユーティリティを実装。
    - etl モジュールは ETLResult を再エクスポート。
  - マーケットカレンダー管理 (src/kabusys/data/calendar_management.py)
    - JPX カレンダー（market_calendar）を使った営業日判定ユーティリティを提供:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days。
    - カレンダーが未取得の場合は曜日ベース（土日を非営業日）でフォールバック。
    - next/prev/get_trading_days は DB 登録値を優先し、未登録日は曜日フォールバックで一貫性を保つ実装。
    - calendar_update_job を実装し、J-Quants API から差分取得・バックフィル（直近 _BACKFILL_DAYS 日）して market_calendar を更新する（jq.fetch_market_calendar / jq.save_market_calendar を呼び出す）。
    - 異常検出（将来日付が過度に離れている等）時の健全性チェックを実装。

- リサーチ / ファクター (src/kabusys/research)
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR、相対 ATR、平均売買代金、出来高比率）、Value（PER, ROE）を計算する関数を実装: calc_momentum, calc_volatility, calc_value。
    - DuckDB に対する SQL ベースの実装で、価格・財務テーブルのみを参照。データ不足時は None を返す設計。
  - 特徴量探索 / 統計 (src/kabusys/research/feature_exploration.py)
    - 将来リターン計算 calc_forward_returns（任意ホライズン対応、horizons の検証あり）。
    - IC（Information Coefficient）算出 calc_ic（スピアマンランク相関: ランク変換は rank を使用）。
    - rank（同順位は平均ランク）と factor_summary（count/mean/std/min/max/median）を実装。
    - pandas 等外部依存を避け、標準ライブラリ + DuckDB のみで実装。

- 実装上の設計・品質考慮（全体）
  - ルックアヘッドバイアス対策：関数内部で datetime.today() / date.today() に依存せず、外部から target_date を受け取る設計。
  - DuckDB のバージョン依存（executemany の空リスト不可など）への対応を実装。
  - OpenAI 呼び出し箇所はテストで差し替え可能に設計（ユニットテストでのモックを想定）。
  - 重要な API エラーはリトライ/バックオフ戦略を採用し、非致命的失敗時はフォールバックして処理継続（フェイルセーフ優先）。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Security
- なし

Notes / 今後の改善候補（開発メモ）
- ai モジュールの OpenAI 呼び出しに対する共通抽象化（重複実装の整理）。
- score_news / score_regime のバッチ設計やコスト削減のためのロギング改善・メトリクス追加。
- etl パイプラインのより詳細な品質チェック結果の取り扱い（アラート／自動リトライ戦略）。
- ドキュメント化（使用例、環境変数の .env.example、DB スキーマ例）を追加。

---- 

この CHANGELOG はソースコードの注釈・実装内容から推測して作成しています。実際の変更履歴やリリースノートとして公開する際は、コミットログやリリース担当の記録に基づいて調整してください。