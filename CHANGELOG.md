# Changelog

すべての重要な変更点は Keep a Changelog のガイドラインに従って記録しています。  
このファイルは日本語で記載しています。

全般的な注意:
- 本リリースはパッケージ初期版の公開想定です（バージョン 0.1.0）。
- DuckDB を主要なローカルデータストアとして利用する設計です。
- OpenAI API（gpt-4o-mini）を使った NLP / センチメント処理機能を含みます。
- ルックアヘッドバイアスを避けるために日時計算は target_date ベースで行い、datetime.today()/date.today() を直接参照しない設計方針を採用しています。

[0.1.0] - 2026-03-28
---------------------------------------

Added
- パッケージ基盤
  - 初期パッケージ化、トップレベルモジュール定義とバージョン情報を追加（src/kabusys/__init__.py）。
  - サブパッケージ公開: data, research, ai, monitoring, strategy, execution（__all__ 等での公開は今後の拡張前提）。

- 環境設定 / ロード（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを追加。
  - 自動 .env 読み込み機能をプロジェクトルート検出（.git または pyproject.toml による）により実装。CWD に依存しないためパッケージ配布後も動作。
  - 読み込み優先順位は OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロード無効化が可能。
  - .env パーサ実装で以下をサポート:
    - export KEY=val 形式
    - シングル／ダブルクォート内のバックスラッシュエスケープ処理
    - インラインコメントの扱い（クォート有無で挙動を区別）
  - 設定に対するバリデーション/取得用のプロパティを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
  - 環境値の制約チェック: KABUSYS_ENV（development/paper_trading/live）、LOG_LEVEL（DEBUG/INFO/...）を検証。is_live / is_paper / is_dev のユーティリティも提供。
  - デフォルト DB パス（DUCKDB_PATH / SQLITE_PATH）の Path 化処理を実装。

- AI：ニュース NLP（src/kabusys/ai/news_nlp.py）
  - raw_news / news_symbols を元に銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄別センチメント（-1.0〜1.0）を生成。
  - ニュース収集ウィンドウ計算（JST 前日 15:00 ～ 当日 08:30 を UTC naive datetime に変換）を提供（calc_news_window）。
  - バッチ処理（1 API 呼び出しで最大 20 銘柄）と、1 銘柄あたり記事数・文字数の上限（_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK）を設定しトークン肥大化を抑制。
  - API 呼び出しに対するリトライ（429 / ネットワーク断 / タイムアウト / 5xx）を指数バックオフで実装。試行回数制御。
  - レスポンスの堅牢なバリデーション実装（JSON 抽出・"results" 構造・コードの正規化・数値チェック・スコアの ±1.0 クリップ）。
  - DuckDB への書き込みは冪等化（該当日・該当コードの DELETE → INSERT）し、部分失敗時に既存スコアを保護する実装。DuckDB 0.10 の executemany の挙動（空リスト不可）を考慮。
  - テスト容易性のため _call_openai_api をパッチ差替え可能に設計。

- AI：市場レジーム判定（src/kabusys/ai/regime_detector.py）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次 market_regime を判定（'bull' / 'neutral' / 'bear'）。
  - マクロ記事抽出用キーワード群と、OpenAI に渡す system prompt を定義。
  - prices_daily から target_date 未満のみを参照することでルックアヘッドを防止。
  - OpenAI 呼び出しに対するリトライとフェイルセーフ（API 失敗時は macro_sentiment=0.0）を実装。
  - 最終結果は market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。DB 書き込み失敗時は ROLLBACK を試行して例外を伝播。

- 研究（research）: ファクター / 特徴量（src/kabusys/research/）
  - factor_research モジュール:
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比）、バリュー（PER・ROE）を計算する関数群を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB 上で SQL とウィンドウ関数を使った実装。データ不足時の扱い（None 返却）を明確化。
  - feature_exploration モジュール:
    - 将来リターン計算（calc_forward_returns）: 任意ホライズン（デフォルト [1,5,21]）に対応、引数検証あり。
    - IC（calc_ic）: スピアマンランク相関の計算、レコード不足や分散ゼロの扱い（None を返す）。
    - ランク関数（rank）: 同順位は平均ランク、浮動小数丸めで ties の扱い安定化。
    - 統計サマリ（factor_summary）: count/mean/std/min/max/median を計算。
  - research/__init__.py で主要 API を再公開。

- データ管理（src/kabusys/data/）
  - calendar_management:
    - market_calendar に対する判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を提供。DB にデータがある場合は DB 値優先、未登録は曜日ベースでフォールバックする一貫したロジックを実装。
    - カレンダー夜間バッチ update_job を実装（calendar_update_job）：J-Quants API から差分取得、バックフィル（直近 _BACKFILL_DAYS を再取得）、健全性チェック（過度に将来の日付はスキップ）を行う。
    - DB がまばらな場合でも next/prev の挙動が一貫するよう設計。
  - pipeline / ETL:
    - ETLResult データクラスを追加して ETL 実行結果（取得数、保存数、品質問題一覧、エラー要約）を保持・辞書化するインターフェースを提供。
    - pipeline モジュールは差分更新・保存（jquants_client 経由の冪等保存）・品質チェックを行う設計方針を文書化（実装の一部を含む）。
    - デフォルトのバックフィル日数、最小データ日付など ETL パラメータを定義。

Changed
- ドキュメント化:
  - 各モジュールに詳細な docstring を追加し設計方針、ルール（ルックアヘッド回避、フェイルセーフ動作、テストのしやすさ）を明示。
  - SQL クエリやウィンドウ幅などの定数をモジュールレベルで定義して可読性・保守性を向上。

Fixed
- N/A（初期リリースのため主に機能追加・設計の整備を行っています）。

Notes / Implementation details
- OpenAI 連携
  - 全ての OpenAI 呼び出しは gpt-4o-mini を想定し、JSON Mode（response_format={"type": "json_object"}）による厳密な JSON 出力を期待する実装。
  - テスト用途に _call_openai_api を patch することで外部 API をモック可能。
- DuckDB 互換性
  - executemany に対して空リストを渡すと失敗するバージョン（例: DuckDB 0.10）を考慮して、空チェックを事前に行う実装。
  - DuckDB から返る日付値を安全に date に変換するユーティリティを追加。
- ログ/監視
  - 重要な警告やフェイルセーフ分岐（API パース失敗、データ不足、ROLLBACK 失敗など）に対して logger でログ出力を行う。
- セキュリティ
  - 環境変数の必須チェックは _require で ValueError を投げ、起動時に誤設定を早期に検出。

Removed
- N/A

Unreleased
- 今後の予定（例）
  - monitoring / execution / strategy の具体的な実装を拡充し、自動売買ワークフローと監視アラートを追加予定。
  - jquants_client の詳細実装、より細かな品質チェックルールの実装。
  - テストカバレッジ強化（CI でのモックを使った OpenAI / J-Quants キャプチャテスト等）。

もし特定ファイルや機能についてより詳細な変更説明（例: SQL クエリの意図、レスポンスフォーマットの詳細、想定テーブル定義など）が必要であれば教えてください。必要に応じて追記・分割して CHANGELOG を拡張します。