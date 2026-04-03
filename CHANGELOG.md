# CHANGELOG

すべての重要な変更点を記録します。本ファイルは Keep a Changelog の形式に準拠しています。  
バージョン番号は semantic versioning に従います。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-03

初期リリース。日本株自動売買プラットフォームのコアライブラリを提供します。主な追加点は以下の通りです。

### Added
- パッケージ基礎
  - パッケージ名: kabusys、初期バージョン 0.1.0 を定義。
  - サブパッケージ公開: data, research, ai, execution, strategy, monitoring などを __all__ で公開。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルートの検出: .git または pyproject.toml を基準に検索するため CWD に依存しない。
    - 読み込み順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - .env パーサー: export 付き形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント解釈等に対応。
    - 上書き制御: override と protected キー（OS 環境変数の保護）をサポート。
  - Settings クラスでアプリケーション設定をプロパティとして公開。
    - J-Quants / kabu ステーション / LINE API / データベースパス（DuckDB / SQLite）/監視閾値 / 環境種別（development/paper_trading/live）などを扱う。
    - 必須キー未設定時に明確な ValueError を送出する _require 実装。
    - env / log_level のバリデーション（許容値チェック）。

- データプラットフォーム (kabusys.data)
  - ETL パイプライン基盤（kabusys.data.pipeline）
    - ETLResult データクラスを定義し、取得/保存件数、品質問題、エラー一覧等を集約可能。
    - 差分取得・バックフィル・品質チェックの設計に対応するユーティリティを含む。
  - ETL の公開インターフェース（kabusys.data.etl）で ETLResult を再エクスポート。
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを利用した営業日判定ロジックを提供。
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を実装。
    - DB 未取得時は曜日ベースのフォールバック（週末を非営業日扱い）。
    - 夜間バッチ更新 job (calendar_update_job)：J-Quants から差分取得して冪等保存、バックフィルと健全性チェックを実装。
    - 最大探索範囲制限や NULL 値に対する警告ログなど堅牢化。
  - jquants_client（参照）経由での保存処理を想定（fetch/save 呼び出し点を用意）。

- リサーチ / ファクター計算 (kabusys.research)
  - factor_research モジュール
    - モメンタムファクター (calc_momentum): 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）を計算。
    - ボラティリティ / 流動性 (calc_volatility): 20日 ATR、相対 ATR、20日平均売買代金、出来高比などを計算。
    - バリューファクター (calc_value): raw_financials から EPS/ROE を取得して PER/ROE を計算（EPS が 0/欠損の場合は None）。
    - DuckDB を用いた SQL ベース実装で、prices_daily / raw_financials のみ参照。外部 API へはアクセスしない設計。
  - feature_exploration モジュール
    - 将来リターン計算 (calc_forward_returns): 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - IC 計算 (calc_ic): Spearman（ランク相関）による Information Coefficient を実装（必要データ不足時は None を返す）。
    - ランク変換ユーティリティ (rank): 同順位は平均ランクを割り当てる実装。
    - 統計サマリー (factor_summary): count/mean/std/min/max/median を算出。
  - 研究用ユーティリティは pandas など外部依存を持たない純粋 Python 実装。

- AI / ニュース NLP（kabusys.ai）
  - news_nlp モジュール (score_news)
    - raw_news と news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini）へバッチ送信。
    - JSON Mode を利用し、最大バッチサイズ 20 銘柄、1 銘柄あたり最大 10 記事・3000 文字にトリム。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライ。
    - レスポンス検証: JSON パース、"results" リスト、各要素の code/score の型検証、未知コードの無視、数値でないスコアのログ警告。
    - スコアは ±1.0 にクリップし、成功分のみ ai_scores テーブルへ置換的に書き込み（DELETE→INSERT、トランザクション、部分失敗保護）。
    - ルックアヘッドバイアス防止のため datetime.today() を参照せず、calc_news_window による厳密な時間窓を使用。
    - API キーは引数または環境変数 OPENAI_API_KEY で解決。未設定時は ValueError。
  - regime_detector モジュール (score_regime)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）と、news_nlp によるマクロセンチメント（重み30%）を合成して市場レジーム（bull/neutral/bear）を日次判定。
    - マクロニュースはキーワードフィルタで抽出（複数の日本語・英語キーワード）。
    - OpenAI 呼び出しは専用の内部関数を使用し、API レイヤの分離（モジュール結合軽減）。
    - API 呼び出し失敗やパース失敗は macro_sentiment=0.0 にフォールバックするフェイルセーフ実装。
    - 計算結果は market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。書き込み失敗時は ROLLBACK を試行し例外を伝播。

- インフラ / 安全対策
  - DuckDB を主要なローカル DB として想定し、SQL 内での窓関数や ROW_NUMBER を活用した互換性重視の実装。
  - トランザクション/ROLLBACK によるデータ整合性確保の実装。
  - ルックアヘッドバイアス防止の設計方針が各所に反映（日時取得の明示的回避、クエリの排他条件）。
  - ロギング（logger）を多用し、処理状況や警告・失敗事象を記録。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Security
- OpenAI API キー等の機密値は Settings 経由で取得し、.env の自動ロードは環境変数で無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。
- .env の読み込み時に OS 環境変数を protected として上書き防止する仕組みを導入。

### Notes / 暫定的な制約
- 本リリースでは外部クライアント（jquants_client）や kabu ステーション API の具象実装は呼び出し参照に留め、実際の API クライアントは別モジュールでの実装を想定しています。
- DuckDB の executemany に関する互換性（空リスト禁止）を考慮した実装が含まれています。
- OpenAI 呼び出しは gpt-4o-mini（JSON mode）を想定。API バージョン差分への耐性としてレスポンス検証と例外ハンドリングを多めに実装しています。

---

作成・変更に関する詳細や追加情報が必要であればご指示ください。特にリリースノートの粒度（より技術的な実装詳細を列挙する／利用者向けの簡潔な要約にする）を指定していただければ調整します。