# Changelog

すべての注記は「Keep a Changelog」形式に従います。  
このファイルはコードベースの内容から推測して作成した変更履歴です。

なお、バージョンはパッケージ定義（src/kabusys/__init__.py の __version__）に合わせています。

## [Unreleased]
- 今後の変更点をここに記載してください。

## [0.1.0] - 2026-04-01
最初の公開リリース（推定）。以下の主要機能と設計方針を実装しています。

### Added
- パッケージ基盤
  - kabusys パッケージを追加。エクスポートモジュール: data, strategy, execution, monitoring。
  - バージョン: 0.1.0。

- 設定・環境変数管理（kabusys.config）
  - .env / .env.local ファイルの自動読み込み（OS 環境変数 > .env.local > .env の優先順位）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - .env パーサ実装（export プレフィックス、クォート内部のエスケープ、行内コメントの扱いに対応）。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB / 監視 / システム設定等のプロパティを公開（必須変数は _require によりチェック）。
  - 設定値のバリデーション（KABUSYS_ENV, LOG_LEVEL の許容値チェック）。

- AI モジュール（kabusys.ai）
  - news_nlp.score_news
    - raw_news と news_symbols を集約し、銘柄別に記事をまとめて OpenAI（gpt-4o-mini, JSON Mode）へバッチ送信。
    - バッチサイズ、記事数・文字数トリム、JSON レスポンスのバリデーション、スコアの ±1.0 クリップを実装。
    - 再試行（429 / ネットワーク断 / タイムアウト / 5xx）を指数バックオフで処理。失敗はログ記録してスキップ（フェイルセーフ）。
    - DuckDB への書き込みは冪等（既存レコード削除 → 挿入）。DuckDB 0.10 の executemany 空リスト制約に配慮した実装。
  - regime_detector.score_regime
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を算出。
    - マクロニュースはニュース抽出関数を利用し、OpenAI を呼び出して JSON の {"macro_sentiment": ...} を期待。
    - API 呼び出しの再試行、API 失敗時は macro_sentiment=0.0 で継続するフェイルセーフ。
    - DB への書込はトランザクションで冪等に実施（DELETE → INSERT、COMMIT / ROLLBACK）。

- Data モジュール（kabusys.data）
  - calendar_management
    - JPX カレンダー管理ロジック（market_calendar テーブルに依存）。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days 等の営業日判定ユーティリティを提供。
    - DB データがない場合は土日フォールバック。DB とフォールバックの一貫性を保つ設計。
    - calendar_update_job: J-Quants から差分取得し冪等に保存（バックフィル・健全性チェック含む）。
  - pipeline / ETLResult（kabusys.data.pipeline / kabusys.data.etl）
    - ETLResult dataclass により ETL 実行結果を集約（取得件数、保存件数、品質問題、エラー等）。
    - 差分更新・バックフィルの方針、品質チェック（quality モジュールとの連携）を念頭に置いた ETL スケルトン。
    - jquants_client を利用してデータ取得／保存を行う想定（実装はクライアント側に分離）。

- Research モジュール（kabusys.research）
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、ma200 乖離の算出。データ不足時には None を返す動作。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率などの算出。
    - calc_value: raw_financials から最新の財務データを取得し PER / ROE を計算（EPS 欠損時の扱いに注意）。PBR・配当利回りは未実装。
  - feature_exploration
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。horizons の妥当性チェックを実装。
    - calc_ic: スピアマンランク相関（IC）計算。3 銘柄未満は None を返す。
    - factor_summary / rank: 基本統計量算出とランキング処理（同順位は平均ランク、丸めて ties 対策）。

- 監視・運用面の配慮
  - 各モデル・ETL・AI 処理で「ルックアヘッドバイアス」を避ける設計（datetime.today() / date.today() を直接参照しない、target_date を明示）。
  - ロギングと WARNING / INFO レベルでの実行状況記録。
  - API キーは引数で注入可能（テストしやすくするため）。未設定時は ValueError を送出。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Deprecated
- （初期リリースのため該当なし）

### Removed
- （初期リリースのため該当なし）

### Security
- 環境変数ロード時、OS の既存環境変数を protected として .env による上書きを保護する挙動を実装。

## 既知の制約・注意点
- OpenAI API
  - OpenAI API キー（OPENAI_API_KEY）は必須。score_news / score_regime はキーが未設定だと ValueError を送出します。
  - API 呼び出しは gpt-4o-mini を使う想定で JSON Mode を利用するため、モデル側の出力形式に依存します。レスポンスパース失敗時はフェイルセーフでスコア 0.0 またはスキップします。
- DuckDB
  - 実装は DuckDB を前提にしており、テーブル名やカラム名（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials など）に依存します。
  - DuckDB 0.10 の executemany の挙動（空リスト不可）に配慮した実装があります。別バージョンでの互換性に注意してください。
- データ不足
  - 多くの指標（MA200, ATR 等）は必要な履歴が不足すると None / 中立値を返す挙動となっています。実運用時はデータ充足を確認してください。
- 未実装
  - 一部指標（PBR、配当利回り等）は現バージョンでは実装されていません。
- テスト置換
  - OpenAI 呼び出しは内部で _call_openai_api を通す実装になっており、ユニットテスト時に patch による差替えが可能です。

## マイグレーションノート
- 初期リリースのため、既存ユーザー向けの移行作業はありません。ただし:
  - .env の構文（export プレフィックス、クォート・エスケープ、行内コメントの扱い）に互換性要件があるため、既存の .env を利用する場合はパース仕様に合致しているか確認してください。
  - DuckDB スキーマ（テーブル・カラム名）を本リポジトリの SQL スキーマと合わせてください。

---

この CHANGELOG はコードベースの実装内容から推測して作成しています。実際のリリースノートや日付・バージョン管理情報はリポジトリの実際の履歴に合わせて更新してください。