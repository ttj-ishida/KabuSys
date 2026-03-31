# Changelog

すべての非破壊的変更は Keep a Changelog の形式に従って記載しています。  
各リリースの内容は、ソースコードから推測可能な機能実装・設計方針・例外処理等を基にまとめています。

現在のバージョン: 0.1.0

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-31
初期リリース。日本株自動売買システム「KabuSys」の基礎機能群を実装しました。主な追加点と設計上の注意を以下にまとめます。

### Added
- パッケージ基盤
  - kabusys パッケージ初期化（src/kabusys/__init__.py）。バージョン "0.1.0"、公開サブパッケージ: data, strategy, execution, monitoring をエクスポート。

- 設定管理
  - 環境変数 / .env 読み込みユーティリティ（src/kabusys/config.py）。
    - プロジェクトルートを .git または pyproject.toml から検出して .env / .env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。
    - .env 行パーサーは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理等に対応。
    - override / protected オプションにより OS 環境変数保護や .env.local による上書き制御を実装。
    - Settings クラスを提供し、J-Quants・kabuステーション・Slack・DBパス・実行環境（development/paper_trading/live）・ログレベル等のプロパティを定義。未設定時は明示的な例外を投げる設計。
    - env / log_level の値検証（許容値集合）を実装。
    - デフォルトの DB パス（duckdb / sqlite）や kabu API base URL のフォールバック値を用意。

- Data（データ基盤）
  - ETL パイプライン骨格（src/kabusys/data/pipeline.py, etl.py エクスポート）。
    - ETLResult dataclass を提供（取得件数、保存件数、品質チェック結果、エラー等を集約）。
    - 差分取得・バックフィル・品質チェック・id_token 注入などの設計方針を反映。
    - DuckDB を前提とした最大日付取得やテーブル存在チェックなどのユーティリティ実装。
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar を使った営業日判定（is_trading_day）、翌営業日/前営業日取得（next_trading_day / prev_trading_day）、期間内営業日の取得（get_trading_days）、SQ日判定（is_sq_day）を実装。
    - DB登録値を優先し、未登録日は曜日ベース（週末除外）でフォールバックする一貫したロジック。
    - calendar_update_job による J-Quants からの差分取得・バックフィル・健全性チェック（未来日付の異常検知）・冪等保存フローを実装。
    - 最大探索日数の上限（_MAX_SEARCH_DAYS）を設け無限ループを防止。

  - ETL 用の jquants_client 経由の保存・取得フックを想定（jq モジュールの呼び出し点を配置）。

- AI（自然言語処理 / LLM）
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約し、銘柄ごとに記事テキストをまとめ OpenAI（gpt-4o-mini）にバッチ送信してセンチメント（-1.0〜1.0）を取得。
    - バッチ処理（最大 _BATCH_SIZE = 20 銘柄 / チャンク）、1銘柄あたりの最大記事数・文字数トリム、JSON Mode を使った厳密なレスポンス検証を実装。
    - リトライ（429・ネットワーク断・タイムアウト・5xx）を指数バックオフで行い、致命的でない場合はスキップして継続（フェイルセーフ）。
    - レスポンスのバリデーション（JSON パース復元処理、results 配列・code/scoreの検証、数値クリップ）を実装。
    - 書き込みは冪等に DELETE → INSERT を行い、部分失敗時に他銘柄の既存スコアを消さないように配慮（DuckDB 0.10 互換のため executemany の空リスト回避）。
    - テスト容易性のため _call_openai_api を patch できる設計。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - prices_daily / raw_news を参照して MA200 値・マクロニュース取得（キーワードフィルタ）を行い、OpenAI によるマクロセンチメント評価を実施。
    - API リトライ・フェイルセーフ（マクロ評価失敗時は macro_sentiment = 0.0 で継続）を実装。
    - 結果は market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK とログ出力）。

- Research（リサーチ機能）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金、出来高比率）、バリュー（PER, ROE）を DuckDB SQL を用いて計算する関数を実装。
    - データ不足時の None 扱い、営業日ベースでの horizon 設定、ログ出力を備える。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン calc_forward_returns（任意ホライズン、入力検証）、IC（Spearman ρ） calc_ic、ランク付け rank、統計サマリー factor_summary を実装。
    - 外部依存を増やさず標準ライブラリ＋DuckDB で完結する設計。
  - data.stats の zscore_normalize を re-export（src/kabusys/research/__init__.py）。

### Changed
- N/A（初回リリースのため「追加」が中心）

### Fixed
- N/A（初回リリース）

### Security
- 環境変数管理で API キーやトークンなどを環境変数経由で取得し、未設定時は明示的に例外を送出することで誤った動作を防止。
- .env 読み込みは既存の OS 環境変数を保護する仕組み（protected set）を持つ。

### Notes / Known limitations / Migration
- OpenAI の利用
  - score_news / score_regime は OpenAI API キー（api_key 引数 または 環境変数 OPENAI_API_KEY）が必須。未設定時は ValueError を送出します。
  - 使用モデルは gpt-4o-mini、JSON Mode を前提に実装されています。将来 SDK 仕様変更に備えたエラーハンドリングを備えていますが、モデルや SDK の変更により挙動が変わる可能性があります。

- 環境変数必須項目
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID などが必須プロパティとして定義されています。開発時は .env.example を参照して設定してください。

- DuckDB 互換性
  - executemany に対する制約（空リスト不可など）を考慮した実装が複数箇所にあります（ai スコア書き込みなど）。DuckDB のバージョンにより挙動差がある場合は注意してください。

- ルックアヘッドバイアス回避
  - 各モジュール（AI スコア、レジーム判定、ファクター計算等）は datetime.today()/date.today() の直接参照を避け、target_date を明示的に受け取る設計になっています。バックテストや研究用途で再現性が保てます。

- フェイルセーフ設計
  - 外部 API（OpenAI、J-Quants）失敗時は例外を即時上げるのではなく、ログ出力のうえフォールバック値で継続する処理や、問題を集めて ETLResult.errors に格納する設計方針がとられています。運用時はログと ETLResult の内容を確認してください。

### Tests / Extensibility
- テスト容易性: OpenAI 呼び出しを行う内部関数（_call_openai_api）を patch しやすい構造になっており、ユニットテストで API 呼び出しをモック可能です。
- 設計はモジュール分離（AI モジュール間でプライベート関数を共有しない等）を意識しています。

---

この CHANGELOG はソースコードの実装内容から推測して作成しています。詳細なユーザードキュメントや API 仕様、運用手順（環境変数設定、DB スキーマ、J-Quants/kabu API 認証フロー等）は別途整備することを推奨します。