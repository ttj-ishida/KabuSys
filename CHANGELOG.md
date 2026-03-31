Keep a Changelog
=================

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは、https://keepachangelog.com/ja/ のガイドラインに従ってバージョニングしています。

[Unreleased]
------------

- （なし）

[0.1.0] - 2026-03-31
--------------------

Added
- 基本パッケージインターフェースを追加
  - パッケージバージョンを 0.1.0 に設定（src/kabusys/__init__.py）。
  - パブリックAPIとして data, strategy, execution, monitoring をエクスポート。

- 環境設定管理
  - .env ファイルおよび環境変数から設定を自動読み込みする設定モジュールを追加（src/kabusys/config.py）。
    - プロジェクトルートを .git または pyproject.toml を基準に探索して自動読み込み（配布後も CWD に依存しない挙動）。
    - .env と .env.local の読み込み順序を実装（.env.local が優先、既存 OS 環境変数は保護）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - export KEY=val 形式、シングル/ダブルクォート内のエスケープ、インラインコメント処理などを考慮した行パーサを実装。
    - 必須環境変数取得ヘルパ（_require）と Settings クラスを公開。JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID 等を明示。
    - 環境値検証（KABUSYS_ENV の許容値、LOG_LEVEL の検証）と便利なフラグ（is_live/is_paper/is_dev）を提供。
    - データベースパスの設定（DUCKDB_PATH, SQLITE_PATH）の Path 解釈を実装。

- ニュース NLP / LLM 統合（OpenAI）
  - ニュース記事を銘柄単位で集約し、OpenAI（gpt-4o-mini, JSON mode）でセンチメント評価して ai_scores に書き込む score_news を実装（src/kabusys/ai/news_nlp.py）。
    - JST時間ウィンドウ（前日15:00〜当日08:30）を UTC に変換して対象記事を抽出する calc_news_window を実装。
    - 銘柄ごとに最新記事を最大件数・文字数でトリムしてバッチ送信（1回あたり最大20銘柄）。
    - レスポンスのバリデーションと JSON 抽出、スコアの ±1.0 クリッピング。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライの実装。
    - 部分失敗時のデータ保護のため、書き込み前に対象 code の DELETE → INSERT を行う冪等・部分更新戦略。
    - テスト用に _call_openai_api を monkeypatch できる設計（ユニットテストで差替え可能）。

  - マクロセンチメントと ETF MA を組み合わせて市場レジームを判定し market_regime テーブルへ書き込む score_regime を実装（src/kabusys/ai/regime_detector.py）。
    - ETF 1321 の 200 日移動平均乖離（重み70%）と LLM によるマクロセンチメント（重み30%）を合成してレジーム（bull/neutral/bear）を生成。
    - Look‑ahead バイアス防止のため target_date 未満のデータのみを参照する設計。
    - OpenAI 呼び出しは独立実装、失敗時は macro_sentiment=0.0 にフォールバック。
    - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実施。

- データプラットフォーム（DuckDB）関連
  - ETL パイプライン結果を表現する ETLResult データクラスを追加（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py に再公開）。
    - ETL の取得/保存数、品質チェック結果、エラー一覧を格納し、has_errors / has_quality_errors 判定や辞書変換 to_dict を提供。
  - market_calendar（JPX カレンダー）管理ロジックを追加（src/kabusys/data/calendar_management.py）。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を実装。
    - DB がまばらな場合でも曜日ベースのフォールバックを一貫して利用する設計。
    - calendar_update_job による J-Quants からの差分取得・バックフィル・健全性チェック機能を実装。
    - market_calendar の存在チェックや NULL 値に対するログ出力、最大探索日数制限を実装。
  - ETL パイプライン（差分取得、save_* 呼び出し、品質チェック）に関するユーティリティを実装（src/kabusys/data/pipeline.py）。
    - 最小データ開始日、バックフィル日数、カレンダー先読みなどの定数を定義。
    - DuckDB 上の最大日付取得、テーブル存在チェックなど補助関数を実装。
    - ETLResult による結果集約と品質問題の収集をサポート。

- リサーチ / ファクター計算
  - ファクター計算モジュールを追加（src/kabusys/research/factor_research.py）。
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR、相対 ATR、20日平均売買代金等）、Value（PER、ROE）を計算する関数を実装。
    - DuckDB のウィンドウ関数を活用し、営業日ベースのホライズンや窓幅を考慮した実装。
    - データ不足時は None を返す等の堅牢な振る舞い。
  - 特徴量探索ユーティリティを追加（src/kabusys/research/feature_exploration.py）。
    - 将来リターン計算 calc_forward_returns（ホライズン指定、一度のクエリで複数ホライズン対応）。
    - IC（Spearman の ρ）計算 calc_ic、ランク化ユーティリティ rank、列ごとの統計要約 factor_summary を実装。
  - research パッケージ __init__ で主要関数を再エクスポート（src/kabusys/research/__init__.py）。

Changed
- ログ・例外処理方針の明確化
  - AI 呼び出しや DB 操作での失敗時に例外を無闇に投げずログとフォールバック（スコア 0.0 やスキップ）で継続する設計に統一。
  - DuckDB の executemany に関する互換性問題（空リスト不可）に対応する条件分岐を追加。

Fixed
- （初期リリースのため該当なし）

Security
- 環境変数読み込みで OS 環境変数を保護する仕組み（protected set）を導入し、.env による上書きを回避。
- 必須トークン（OpenAI / Slack / kabu / J-Quants 等）を明示し、未設定時は明示的な ValueError を発生させることで秘密情報欠落を早期に検出。

Notes / Implementation details
- OpenAI SDK のレスポンスや例外型の差を吸収する処理（status_code の有無を getattr で参照）を実装して SDK 変更に堅牢化している。
- テスト可能性を考慮して OpenAI 呼び出し用の内部関数は patch で差し替え可能にしている（ユニットテスト容易化）。
- ルックアヘッドバイアス回避のため、すべての「日付基準処理」は target_date 引数を受け取り、date.today()/datetime.today() を直接参照しない設計を採用。
- 一部の設計はドキュメント（DataPlatform.md, StrategyModel.md 等）に基づくことが注釈に明記されている。

開発上の留意点 / 既知の制限
- AI（OpenAI）呼び出しに依存している箇所は API キー必須であり、未設定だと ValueError を投げる。
- ai_scores / market_regime 等のテーブルスキーマは本変更ログには含まれていないため、DB スキーマとの整合が必要。
- 初期リリースのため、エンドツーエンドの運用検証と追加のエラーハンドリングは今後の改善点。

References
- pkg: kabusys 0.1.0 (初回リリース相当)