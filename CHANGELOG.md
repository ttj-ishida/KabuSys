# CHANGELOG

すべての重要な変更はこのファイルに記載します。フォーマットは「Keep a Changelog」に準拠します。  
リリース日はリポジトリの現時点（2026-03-31）に設定しています。

## [Unreleased]

---

## [0.1.0] - 2026-03-31

初期リリース — 日本株自動売買・データ基盤向けのユーティリティ群を実装。

### Added
- 基礎パッケージ情報
  - パッケージバージョンを src/kabusys/__init__.py にて `0.1.0` として定義。
  - 公開モジュール一覧: data, strategy, execution, monitoring。

- 設定・環境変数管理
  - src/kabusys/config.py
    - .env / .env.local の自動ロード機能（プロジェクトルート検出: .git または pyproject.toml）。
    - export 形式・クォート処理・インラインコメント対応の行パーサー実装。
    - 自動ロード無効化用フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - Settings クラスでアプリ設定をプロパティで提供（J-Quants、kabuステーション、Slack、DBパス、監視しきい値、環境・ログレベル等）。
    - 必須値未設定時は ValueError を送出する `_require` 実装。

- AI（ニュースNLP / レジーム判定）
  - src/kabusys/ai/news_nlp.py
    - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini、JSON mode）へバッチ送信して銘柄別センチメントを算出。
    - チャンク処理（最大20銘柄/チャンク）、1銘柄当たりの最大記事数・文字数制限、レスポンスバリデーション実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ。失敗時はスキップして継続（フェイルセーフ）。
    - ai_scores への冪等的書き込み（該当コードのみ DELETE → INSERT）で部分失敗時の保護。
    - テスト容易性のため OpenAI 呼び出し箇所を差し替え可能（ユニットテストでの patch を想定）。
    - 公開 API: score_news(conn, target_date, api_key=None)、calc_news_window 関数。

  - src/kabusys/ai/regime_detector.py
    - ETF 1321（日経225連動）200日移動平均乖離（重み70%）とニュース由来の LLM マクロセンチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出。
    - DuckDB 上の prices_daily / raw_news を参照し、market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - OpenAI 呼び出しのリトライ/フォールバック（API失敗時 macro_sentiment=0.0）。
    - 公開 API: score_regime(conn, target_date, api_key=None)。

- Data（ETL / カレンダー / パイプライン）
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理（market_calendar テーブル）。営業日判定、前後営業日の取得、期間内営業日列挙、SQ 日判定などのユーティリティを実装。
    - DB にデータがない場合は曜日ベースでフォールバック（土日休み）。
    - 夜間バッチ更新ジョブ calendar_update_job 実装（J-Quants クライアント経由で差分取得 → 保存、バックフィル、健全性チェック）。
  - src/kabusys/data/pipeline.py
    - ETLResult データクラス（ETL 実行結果の集約）と ETL 実行時のユーティリティ実装。
    - 差分取得・バックフィル方針、品質チェック（quality モジュール連携）を考慮した設計。
  - src/kabusys/data/etl.py
    - pipeline.ETLResult の再エクスポート。

- Research（ファクター / 特徴探索）
  - src/kabusys/research/factor_research.py
    - モメンタム、ボラティリティ、バリュー等のファクター計算を実装:
      - calc_momentum: 1M/3M/6M リターン、200日MA乖離。
      - calc_volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比率。
      - calc_value: PER、ROE（raw_financials から取得）。
    - DuckDB SQL を活用し prices_daily / raw_financials のみ参照。欠損・データ不足時は None を返す。
  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns: 指定ホライズンの将来リターン取得（horizons のバリデーションあり）。
    - calc_ic: スピアマンランク相関（IC）計算（3件未満で None）。
    - rank: 同順位を平均ランクで扱うランク化ユーティリティ（丸めにより ties の取り扱い安定化）。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を計算。
  - src/kabusys/research/__init__.py
    - 主要関数の公開エクスポート（calc_momentum, calc_value, calc_volatility, zscore_normalize 等）。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Security
- （初期リリースのため該当なし）

### Notes / 設計上の重要ポイント
- ルックアヘッドバイアス対策
  - date.today()/datetime.today() を主要処理で直接参照しない設計（target_date を明示的に渡す）。
  - DB クエリは target_date 未満/排他条件などを使ってルックアヘッドを防止。

- フェイルセーフ / 部分失敗耐性
  - LLM 呼び出しや外部 API 失敗時は例外流出させず、許容可能なデフォルト（例: macro_sentiment=0.0）で継続する箇所がある。
  - ai_scores / market_regime 等への書き込みは冪等的に行い、部分失敗で既存データを不必要に消さない戦略を採用。

- OpenAI（LLM）統合
  - 使用モデル: gpt-4o-mini（JSON Mode を利用する想定）。
  - JSON パースの堅牢化（前後の余計なテキストを { } から抽出する等）。
  - テストのため内部の API 呼び出し関数を patch 可能にしている。

- DuckDB
  - 主な永続層は DuckDB を想定。executemany の空リストバインド制約（DuckDB 0.10）を考慮した実装がある。

- 環境変数ロード
  - プロジェクトルートの自動検出により .env/.env.local を優先順で読み込む。OS 環境変数は保護される設計。
  - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を設定。

- テスト容易化
  - LLM 呼び出し箇所や time.sleep 等を差し替え可能に実装（ユニットテストでのモックを想定）。

---

開発・運用者向け: 各モジュールの docstring に設計方針・前提（例: raw_news.datetime は UTC など）が記載されています。実運用前に環境変数（OpenAI API キー、JQUANTS / KABU API、Slack 設定等）の設定と DuckDB テーブルスキーマ準備を行ってください。