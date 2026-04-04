# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
本ファイルはコードベース（src/kabusys 以下）の内容から推測して作成した初回リリース向けの変更履歴です。

全般的な前提:
- DB: DuckDB を想定（DuckDBPyConnection を引数に取る関数多数）。
- 外部 API: OpenAI（gpt-4o-mini、JSON Mode）および J-Quants を利用。
- 日付処理: ルックアヘッドバイアス防止のため datetime.today()/date.today() を参照しない設計が各所で採用されています。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-04
初回リリース。パッケージの基本機能（データ取得/ETL、マーケットカレンダー管理、ファクター計算、ニュースNLP / レジーム判定、設定管理など）を実装。

### Added
- パッケージ基盤
  - kabusys パッケージ初期化とバージョン管理（__version__ = 0.1.0）。
  - モジュール公開一覧の整備（data, strategy, execution, monitoring を __all__ に登録）。

- 設定・環境管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを実装。
  - プロジェクトルート特定ロジック (_find_project_root) により .git または pyproject.toml を起点に .env 自動読み込みを実行（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - .env パーサー（export 形式、クォート内エスケープ、インラインコメント処理）を実装。
  - 必須環境変数チェック (_require)、環境検証（KABUSYS_ENV, LOG_LEVEL の妥当性チェック）を実装。
  - 各種パスやしきい値（DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH, CPU/MEMORY/DISK閾値 等）を Settings でプロパティとして提供。

- ニュースNLP（kabusys.ai.news_nlp）
  - raw_news / news_symbols を元に銘柄毎のニュースを集約し、OpenAI（gpt-4o-mini・JSON Mode）でセンチメントを評価して ai_scores テーブルへ書き込む score_news を実装。
  - タイムウィンドウ計算（前日15:00 JST ～ 当日08:30 JST）およびチャンク/バッチ処理（1回最大20銘柄）を実装。
  - トークン膨張対策（1銘柄あたり最大記事数/最大文字数でトリム）、API のリトライ（429/ネットワーク/タイムアウト/5xx 用の指数バックオフ）、レスポンスの厳格なバリデーション（JSON抽出、results の検証）を実装。
  - DuckDB への冪等書き込み（DELETE → INSERT、部分失敗時に他コードを保護）と、空パラメータに対する注意（DuckDB executemany の制約）を反映。
  - テスト容易性のため _call_openai_api を分離してパッチ可能に。

- マーケットレジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（Nikkei 225 連動型）200日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次レジーム（bull/neutral/bear）を計算する score_regime を実装。
  - ma200_ratio 計算（target_date 未満のデータのみ使用してルックアヘッド回避）、マクロ記事抽出、および OpenAI 呼び出し（リトライ・フェイルセーフで macro_sentiment=0.0 にフォールバック）を実装。
  - market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を行う。
  - マクロキーワード集や閾値などの定数を定義（モデル gpt-4o-mini、最大記事数、リトライポリシー等）。

- リサーチ（kabusys.research）
  - factor_research モジュール: calc_momentum, calc_volatility, calc_value を実装。
    - Momentum: 1M/3M/6M リターンおよび 200 日 MA 乖離（データ不足時は None / 中立扱い）。
    - Volatility: 20日 ATR（true_range を適切に扱う）、相対ATR、20日平均売買代金、出来高比率等。
    - Value: raw_financials から最終財務データを取得して PER / ROE を計算（EPS 0 や欠損時の扱いに注意）。PBR/配当利回りは未実装で注記あり。
  - feature_exploration モジュール:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを LEAD を使って一括取得。
    - calc_ic: ファクターと将来リターンの Spearman ランク相関（IC）を実装（有効レコード <3 の場合は None）。
    - rank, factor_summary: ランク化（同順位は平均ランク）と基本統計量サマリー（count/mean/std/min/max/median）を実装。
  - zscore_normalize を data.stats から再公開（research パッケージの __init__ にて）。

- データ基盤（kabusys.data）
  - calendar_management: JPX カレンダー運用機能を実装。
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
    - market_calendar が未存在/未登録の場合は曜日ベースのフォールバック（週末除外）を使用する一貫した振る舞い。
    - calendar_update_job: J-Quants からの差分取得、バックフィル、健全性チェック、冪等保存フローを実装。
  - pipeline / etl:
    - ETLResult データクラスを実装（取得件数・保存件数・品質問題・エラー一覧などを保持）。
    - ETL パイプライン設計に関する基本的なユーティリティの骨組みを実装（差分更新・バックフィル・品質チェック統合・id_token 注入を想定）。
    - data.etl で ETLResult を再エクスポート。

- ロギングと堅牢性
  - 各モジュールで詳細な logger 呼び出し（info/warning/exception/debug）を追加。
  - API 呼び出しの失敗は原則フェイルセーフ（可能な限りスキップして処理継続）する設計。
  - DuckDB との相互運用性（executemany の空リスト制約等）に配慮した実装。

### Changed
- 初版のため過去バージョンからの変更はなし（このリリースで主要機能をまとめて追加）。

### Fixed
- 初版のため修正項目はなし。

### Security
- 環境変数による機密情報管理を採用（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、OPENAI_API_KEY 等）。必須値未設定時は ValueError を投げる（明示的な失敗）。
- 自動 .env 読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD により明示的に無効化可能でテストや CI に配慮。

### Notes / Known limitations
- OpenAI のレスポンスは JSON Mode を期待するが、実運用でのレスポンスのばらつき（前後に余計なテキストが入る等）を想定し補正ロジックを含む。
- calc_value では現時点で PBR や配当利回りは未実装（将来追加予定と注記あり）。
- ニュースおよびレジーム判定は外部 API（OpenAI）依存のため、API 制限や料金に注意が必要。
- 日付参照について各所で「ルックアヘッドバイアス防止」の設計がなされており、target_date を呼び出し側で明示的に渡す設計になっています。運用時は適切な target_date を渡すこと。

---

この CHANGELOG はコード全体の記述と設計注釈に基づき推測して作成しています。実際のリリースノートとして利用する場合は、変更点・バグ修正・既知問題・マイグレーション手順などを追加で確認・追記してください。