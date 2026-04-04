# Changelog

すべての注目すべき変更点を記録します。本ファイルは Keep a Changelog の形式に準拠しています。  
慣例によりバージョンはセマンティックバージョニングを使用します。

## [Unreleased]

## [0.1.0] - 2026-04-04
初期リリース。

### Added
- パッケージ基盤
  - パッケージ名を kabusys として公開。top-level の __all__ に data / strategy / execution / monitoring を想定したエクスポートを定義（現状実装済みのサブパッケージ群を含む構成）。
  - バージョン情報: `kabusys.__version__ = "0.1.0"`。

- 環境設定・ロード機能（kabusys.config）
  - .env ファイル / .env.local または OS 環境変数から設定を読み込む自動ローダを実装。
  - プロジェクトルート検出は __file__ を起点に `.git` または `pyproject.toml` を探索する方式で CWD に依存しない設計。
  - .env パーサーの強化:
    - コメント行（#）や `export KEY=val` 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応。
    - クォート無しの値のインラインコメント処理を柔軟に扱う。
  - 自動ロードの無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート（テスト用途など）。
  - 環境設定のプロパティ群（Settings）を提供:
    - J-Quants / kabuステーション / LINE / データベースパス / 監視設定 / システム設定等のアクセス用プロパティを用意。
    - 必須値取得時のバリデーション（不足時は ValueError を送出）。
    - `KABUSYS_ENV` に対する値検証（development / paper_trading / live のみ許容）。
    - `LOG_LEVEL` 検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約して OpenAI（gpt-4o-mini, JSON mode）へバッチ送信し、銘柄ごとのセンチメント ai_score を ai_scores テーブルへ保存。
    - 処理のポイント:
      - タイムウィンドウは JST ベース（前日 15:00 ～ 当日 08:30）を UTC に変換して使用（calc_news_window 実装）。
      - 1 銘柄あたり最大記事数・最大文字数でトリムしてトークン肥大を防止。
      - 最大バッチサイズやリトライ（429/ネットワーク断/5xx/タイムアウト）を実装、指数バックオフ。
      - レスポンスの堅牢なバリデーションと JSON パース回復処理（余分なテキストから {} を抽出するロジック）。
      - 成功した銘柄コードのみを DELETE → INSERT で置換（冪等性・部分失敗からの保護）。
      - API 呼び出し箇所はテスト容易性のため差し替え可能（関数単位で patch 可能）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成し、日次で市場レジーム（bull/neutral/bear）を判定して market_regime テーブルへ保存。
    - 処理のポイント:
      - DuckDB からの価格取得は look-ahead を防ぐため target_date 未満のデータのみ使用。
      - マクロニュースは news_nlp の窓計算(calc_news_window)と同様に収集し、LLM（gpt-4o-mini）へ送信して JSON スコアを取得。
      - LLM/ネットワーク失敗時はフェイルセーフとして macro_sentiment = 0.0 を使用（例外を投げず継続）。
      - 書き込みは BEGIN/DELETE/INSERT/COMMIT のトランザクションで冪等に実行。失敗時は ROLLBACK を試行し、上位へ例外を伝播。
      - OpenAI SDK 周りの 5xx / RateLimit などに対するリトライ処理を実装。

- リサーチモジュール（kabusys.research）
  - factor_research:
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離 (ma200_dev) を計算（データ不足時は None を返す）。
    - Volatility: 20 日 ATR（平均 true range）、相対 ATR、20 日平均売買代金、出来高比率を計算。
    - Value: raw_financials から最新の EPS/ROE を取得し PER / ROE を計算（EPS が 0 または欠損時は None）。
    - 全て DuckDB の prices_daily / raw_financials のみ参照、外部 API に依存しない。
    - 結果は (date, code) をキーとする dict のリストで返す。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）: 複数ホライズン（デフォルト [1,5,21]）対応、入力検証、一括 SQL 取得で効率化。
    - IC 計算（calc_ic）: スピアマンのランク相関を計算、サンプル不足時に None を返す。
    - ファクター統計サマリー（factor_summary）とランク付けユーティリティ（rank）。
  - data.stats の zscore_normalize を再エクスポートすることで標準化ユーティリティを提供。

- データプラットフォーム（kabusys.data）
  - calendar_management:
    - market_calendar テーブルの管理と営業日判定ユーティリティを提供（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB にカレンダー情報が存在しない場合は曜日ベース（土日除外）のフォールバックを使用。
    - 夜間バッチ calendar_update_job を実装（J-Quants API から差分取得 → 保存、バックフィルや健全性チェックを実施）。
    - 最大探索日数やバックフィル期間、先読み日数などの定数を定義して無限ループやデータ異常を防止。
  - pipeline / etl:
    - ETLResult データクラスを実装（取得数・保存数・品質問題・エラー一覧等を保持）。
    - ETL の設計方針（差分更新・バックフィル・品質チェックの扱い・id_token 注入等）を実装方針として反映。
    - jquants_client 経由の保存は冪等（ON CONFLICT DO UPDATE）を想定。
    - ETLResult は辞書化(to_dict)してロギング等に利用可能。
  - etl モジュールは pipeline.ETLResult を再エクスポート。

- DuckDB を一貫して使用
  - ほとんどのデータアクセス層・リサーチ処理は DuckDB 接続を受け取り SQL を主体に実装。
  - トランザクション (BEGIN/COMMIT/ROLLBACK) を利用して DB 書き込みの一貫性を確保。

- ロギング・エラーハンドリング
  - 各モジュールで logger を使用し情報・警告・例外ログを適切に出力。
  - API 呼び出しに関してはリトライ戦略・非致命的フォールバックを採用し、処理を継続できるよう設計。

### Changed
- （初期リリースのため変更履歴はなし）

### Fixed
- （初期リリースのため修正履歴はなし）

### Security
- 必須の機密情報（J-Quants の refresh token、kabu API パスワード、OpenAI API キーなど）は環境変数での供給を想定。アプリ内にハードコードされることはない。
- 自動 .env ロード機能はテストや特別な環境のために無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

### Breaking Changes
- なし（初回公開）

### Migration / 注意事項
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN（J-Quants API 用）
  - KABU_API_PASSWORD（kabuステーション API 用）
  - OPENAI_API_KEY（AI スコアリング用。score_news / score_regime は未指定時に ValueError を送出）
- 任意設定例:
  - KABUSYS_ENV は "development" / "paper_trading" / "live" のいずれかを設定してください（デフォルト: development）。
  - デフォルトのデータベースパスは DUCKDB_PATH="data/kabusys.duckdb"、モニタリング用 SQLITE_PATH="data/monitoring.db"。
  - PID / KILL flag のパスや閾値（CPU/MEM/DISK）などは環境変数で調整可能。
- OpenAI 呼び出しのテスト:
  - AI モジュール内の _call_openai_api 関数はユニットテストで差し替え可能（unittest.mock.patch を想定）。
- DuckDB executemany の制約により、空パラメータの実行を避けるガード（if params）を実装しているため、古い DuckDB バージョンとの互換性に配慮。

---

（注）本 CHANGELOG は現在のコードベースから機能・設計方針・挙動を推測して作成した初期開発向けの記録です。追加のサブパッケージ（strategy, execution, monitoring 等）の詳細実装が追加された場合は、次回リリースで機能追加・変更点を明確に追記してください。