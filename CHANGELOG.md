# CHANGELOG

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
このファイルは、リポジトリ内のソースコード（src/kabusys 以下）から実装内容を推測して作成した初版の変更履歴です。

フォーマット:
- Unreleased: 現在未リリースの変更（空の場合は将来用）
- 各リリース: 日付とカテゴリ別の変更概要（Added, Changed, Fixed, Deprecated, Removed, Security）

なお、バージョン情報はパッケージ top-level の __version__ = "0.1.0" に基づいています。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-01
初回公開リリース。日本株のデータ基盤、リサーチ、AI 補助のスコアリング、および設定管理に関するコア機能を実装しています。

### Added
- パッケージ基本情報
  - kabusys パッケージ初期化（src/kabusys/__init__.py）。__version__ と公開サブパッケージ定義。

- 環境設定 / 設定管理（src/kabusys/config.py）
  - .env ファイルと環境変数から設定を読み込む自動ローダーを実装（プロジェクトルート判定: .git / pyproject.toml）。
  - .env ファイルのパースは export 形式やクォート・エスケープ・インラインコメントを考慮。
  - 自動ロードを環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB / 監視 / システム設定（KABUSYS_ENV, LOG_LEVEL）をプロパティで取得・検証。
  - 必須環境変数未設定時は ValueError を送出するユーティリティ _require。

- AI モジュール（src/kabusys/ai）
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini / JSON mode）にバッチ送信して銘柄ごとのセンチメント ai_score を ai_scores テーブルへ保存する score_news 関数を実装。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で提供。
    - バッチサイズ・トリム（記事数・文字数制限）・リトライ（429・ネットワーク・5xx）・レスポンス検証を実装。
    - DuckDB 互換性のため executemany の空パラメータ回避等の注意点を考慮した実装。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動ETF）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
    - prices_daily と raw_news を参照し、market_regime テーブルへ冪等的に書き込む（BEGIN/DELETE/INSERT/COMMIT）。
    - OpenAI 呼び出しは内部実装で行い、API エラー時は macro_sentiment=0.0 のフォールバック。
    - API 呼び出しのリトライ・バックオフを実装。

- データプラットフォーム / ETL（src/kabusys/data）
  - calendar_management.py
    - market_calendar を用いた営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。DB にデータがない場合は曜日ベースでフォールバック。
    - JPX カレンダーの夜間バッチ更新 calendar_update_job を実装（J-Quants クライアントを使用した差分取得・バックフィル・健全性チェック）。
  - pipeline.py / etl.py
    - ETL パイプラインの結果を表す ETLResult データクラスを実装して公開（etl.py で再エクスポート）。
    - 差分取得、品質チェック（quality モジュール呼び出しの想定）、保存処理のためのユーティリティ関数を実装。
    - DuckDB のテーブル存在チェックや最大日付取得等の内部ユーティリティを実装（ETL 実装の下地）。

- Research（src/kabusys/research）
  - factor_research.py
    - モメンタム（1M/3M/6M、ma200乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金・出来高比率）、バリュー（PER, ROE）の計算関数（calc_momentum, calc_volatility, calc_value）を実装。prices_daily / raw_financials を参照。
  - feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク変換（rank）、統計サマリー（factor_summary）を実装。外部ライブラリに依存しない純 Python 実装。
  - research パッケージの __init__ で主要 API を公開（zscore_normalize を data.stats から再エクスポート）。

- モジュール間の設計・運用上の配慮
  - すべてのモジュールでルックアヘッドバイアス回避のために datetime.today()/date.today() を直接参照しない（外部から target_date を受け取る設計）。
  - DB 書き込みは冪等性を重視（DELETE→INSERT 等）し、部分失敗時に既存データを保護する戦略を採用。
  - OpenAI API 呼び出しは JSON 出力を想定し、レスポンスパース失敗時はフェイルセーフでスキップまたは 0.0 を返す実装。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- OpenAI やその他 API キーは外部から注入することを想定（api_key 引数または環境変数 OPENAI_API_KEY）。未設定時は明示的に例外を投げて通知。
- .env 自動読み込みはプロジェクトルート基準で行うが、意図的に無効化するための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を提供。

### Notes / Implementation details（重要な挙動・互換性注意）
- DuckDB 互換性:
  - executemany に空リストを渡せないバージョン（例: DuckDB 0.10）の挙動を回避するため、空パラメータは予めチェックして処理をスキップする実装がある。
- OpenAI 呼び出し:
  - gpt-4o-mini を使った Chat Completions + JSON mode を前提にしており、API エラー（429 / ネットワーク / タイムアウト / 5xx）に対して指数バックオフでリトライする実装あり。API の SDK 変化に対応するため status_code の取得は getattr で安全に行う。
- フォールバックポリシー:
  - マクロセンチメント評価やニューススコア取得で API が利用できない場合は 0.0 にフォールバック（システム継続性を優先）。
  - market_calendar データがない場合は曜日ベース（平日を営業日）で判断するフォールバックを採用。
- レジーム判定 / スコアの取り扱い:
  - レジームスコアは -1.0〜1.0 にクリップし、閾値に基づいて label を bull / neutral / bear に分類。
- 日付取り扱い:
  - calc_news_window などは JST を基準に計算し、DB の raw_news.datetime は UTC 保存を前提にしている点に注意。

---

今後のリリース候補（例）
- Unreleased に以下のような改善を予定:
  - strategy / execution / monitoring サブパッケージの実装（現在 __all__ に含まれているが未記載の API が存在するため、発展予定）。
  - テストカバレッジ拡充とモック用フックの整理（OpenAI 呼び出しの差し替え容易化等）。
  - パフォーマンス改善（ETL の並列化、DuckDB クエリの最適化）。

（以上）