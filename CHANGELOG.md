# CHANGELOG

すべての注目すべき変更を記録します。本ファイルは「Keep a Changelog」の形式に準拠します。  
初期リリースの内容はリポジトリ内のコード（docstring、関数名、定数、設計方針など）から推測してまとめています。

なおバージョン番号はパッケージの __version__ に基づきます。

## [Unreleased]
- （現時点では未リリースの変更はありません）

## [0.1.0] - 2026-04-03

注記: 日付はコードベースの初期バージョン公開日（推定）として付与しています。

### Added
- パッケージ基本構造を追加
  - kabusys パッケージの公開モジュール: data, strategy, execution, monitoring（src/kabusys/__init__.py）
  - バージョン情報: 0.1.0

- 環境設定・自動 .env ロード機能（src/kabusys/config.py）
  - .env / .env.local の自動読み込み（優先度: OS 環境変数 > .env.local > .env）
  - 読み込みを無効にするフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - プロジェクトルート検出: .git または pyproject.toml を基準に探索（CWD 非依存）
  - .env パーサの実装: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、コメント処理に対応
  - 環境変数アクセスラッパー Settings クラスを提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（data/monitoring.db）
    - 監視関連ファイルパス（PID / kill flag）およびしきい値（CPU/MEM/DISK）
    - KABUSYS_ENV（development / paper_trading / live の検証）および LOG_LEVEL 検証
    - is_live / is_paper / is_dev のユーティリティプロパティ

- ニュース NLP / 市場レジーム検出（AI 機能）（src/kabusys/ai/*）
  - news_nlp モジュール（score_news）
    - ニュース収集ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST を UTC で扱う calc_news_window）
    - raw_news / news_symbols から銘柄ごとに記事を集約し、1銘柄あたり最大記事数・文字数でトリム
    - OpenAI（gpt-4o-mini）の JSON mode を用いたバッチスコアリング（最大 20 銘柄 / チャンク）
    - 再試行ロジック（429/ネットワーク/タイムアウト/5xx に対する指数バックオフ）
    - レスポンス検証およびスコアの ±1.0 クリップ
    - 書き込みは冪等（DELETE → INSERT の部分書換え）で部分失敗時に既存データを保護
    - テスト容易性: _call_openai_api の差し替え可、datetime.today() を参照せずルックアヘッドバイアス回避
    - 返却値: 書き込んだ銘柄数
  - regime_detector モジュール（score_regime）
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）と、マクロセンチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）判定
    - prices_daily からの ma200_ratio 計算（ルックアヘッド回避のため target_date 未満のみ使用）
    - raw_news からマクロキーワードでフィルタしたタイトル収集（キーワード一覧を定義）
    - OpenAI 呼び出しによるマクロセンチメント評価（gpt-4o-mini, JSON 出力想定）
    - API 失敗時は macro_sentiment = 0.0 にフォールバック（フェイルセーフ）
    - リトライロジック（RateLimit / 接続エラー / タイムアウト / 5xx に対する再試行）
    - market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）
    - 閾値とスコア合成ロジック（スケール・クリップ・閾値でラベル決定）
    - テスト容易性とモジュール結合低減のため一部内部関数を分離

- リサーチ（ファクター計算・特徴量探索）（src/kabusys/research/*）
  - factor_research モジュール
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日 MA 乖離）を DuckDB SQL で一括計算
    - calc_volatility: 20日 ATR（atr_20）、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算
    - calc_value: raw_financials から最新財務（EPS/ROE）を取り、PER/ROE を計算（EPS=0 の場合は None）
    - 設計方針: DuckDB 接続のみ使用、外部 API や発注機能にアクセスしない
  - feature_exploration モジュール
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを LEAD で一括算出。horizons の検証と最大探索範囲の最適化
    - calc_ic: スピアマンのランク相関（Information Coefficient）をランク変換して計算（null/非有限値除外、サンプル数閾値あり）
    - rank: 同順位は平均ランク扱い。浮動小数の丸めで ties 検出誤差を低減
    - factor_summary: count/mean/std/min/max/median を標準ライブラリのみで算出
    - 設計方針: pandas 等の外部依存を避ける

- データプラットフォーム（src/kabusys/data/*）
  - calendar_management モジュール
    - JPX カレンダーの管理（market_calendar テーブルの参照・更新ロジック）
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day といった営業日判定ユーティリティ
    - DB に値があれば優先、未登録日は曜日ベースでフォールバック（週末除外）
    - カレンダーの夜間バッチ更新 job（calendar_update_job）を実装（J-Quants クライアント経由で差分取得 → 保存）
    - バックフィル、健全性チェック、探索上限（_MAX_SEARCH_DAYS）等により無限ループや API 側の異常を緩和
  - pipeline / etl / ETLResult
    - ETLResult データクラス（取得件数、保存件数、品質問題リスト、エラー一覧、ユーティリティプロパティと to_dict）
    - pipeline のユーティリティ関数（差分取得、保存、品質チェックを想定する実装方針と定数）
    - etl モジュールは pipeline.ETLResult を再エクスポート（公開インターフェース）

- DuckDB を用いたデータ処理を前提とした多くの関数を実装（全体で DuckDB の接続オブジェクトを引数に受け取る設計）
  - SQL ベースでの window 関数利用、パフォーマンス配慮（スキャン範囲の制限、バッファ日数）
  - DuckDB バージョン差異（executemany の空リスト回避、list 型バインドの互換性）への配慮

- ロギング、警告、フェイルセーフを多用
  - API エラーやデータ不足時に例外を上位へ投げずに継続するケース（フェイルセーフ）を多数実装
  - DB 書き込み時のトランザクション管理（BEGIN/COMMIT/ROLLBACK）とロールバック失敗時の警告ログ

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーの取り扱いは引数注入または環境変数（OPENAI_API_KEY）を使用。コード上でのハードコーディングは行っていない（docstring により注意喚起）。

---

補足（設計・テスト方針の要約）
- ルックアヘッドバイアス防止: 日付処理は target_date ベースで行い、datetime.today() を参照しない実装を遵守。
- テスト容易性: OpenAI 呼び出しなど外部依存は内部関数をモック差し替え可能な構成にしている。
- 部分失敗耐性: AI スコアや ETL の一部失敗時でも他データを保護する設計（書き込み前に対象コードを限定して DELETE/INSERT する等）。

もし特定モジュール（例: pipeline の残り実装、jquants_client の API 契約、strategy / execution / monitoring の詳細）について CHANGELOG に追記したい点や、日付・バージョン表記の修正希望があれば教えてください。