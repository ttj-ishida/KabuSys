Changelog
=========
すべての重要な変更をここに記録します。  
このファイルは Keep a Changelog 準拠のフォーマットで記載しています。

※ バージョンはパッケージの __version__（src/kabusys/__init__.py）に合わせています。

## [0.1.0] - 2026-03-27
初回公開リリース（初期実装）。主な追加点・設計方針は以下の通りです。

### Added
- パッケージ基盤
  - パッケージエントリポイントを追加（kabusys.__init__）。公開モジュールとして data, strategy, execution, monitoring をエクスポート。
  - バージョン情報 __version__ = "0.1.0" を設定。

- 設定・環境変数管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。プロジェクトルートは .git または pyproject.toml を基準に特定（CWD 非依存）。
  - .env パーサーは下記をサポート・考慮：
    - export KEY=val 形式に対応
    - シングル／ダブルクォート内のバックスラッシュエスケープ対応
    - クォートなし行でのインラインコメント認識（直前がスペース/タブの場合）
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env 読み込み時の保護（既存の OS 環境変数は protected として上書き制御）を実装。
  - Settings クラスを提供し、アプリケーションで使用する設定値（J-Quants / kabu API / Slack / DB パス / 環境 / ログレベル判定等）をプロパティ経由で取得可能。必須キー未設定時は明示的な例外を送出。
  - KABUSYS_ENV と LOG_LEVEL の値検証を実装（許容値に外れると ValueError）。

- データプラットフォーム（kabusys.data）
  - ETL パイプライン基盤（pipeline.py）を実装。
    - ETLResult データクラスを定義（取得件数、保存件数、品質問題、エラー要約など）。to_dict によるシリアライズをサポート。
    - 差分取得とバックフィル、品質チェックの考慮点を実装方針として明確化。
  - ETLResult を kabusys.data.etl から再エクスポート。
  - カレンダー管理モジュール（calendar_management.py）を実装。
    - market_calendar テーブルを用いた営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫した挙動。
    - 夜間バッチ calendar_update_job を実装（J-Quants API から差分取得、バックフィル、健全性チェック、冪等保存）。
    - 最大探索範囲・先読み・バックフィル・健全性チェック等の安全策を導入。

- AI（自然言語処理）機能（kabusys.ai）
  - ニュース NLP スコアリング（news_nlp.py）
    - raw_news + news_symbols を集約し、銘柄別にニュースを結合して OpenAI（gpt-4o-mini）へバッチ送信しセンチメントを算出。
    - タイムウィンドウ定義（前日 15:00 JST ～ 当日 08:30 JST）と UTC 変換（calc_news_window）。
    - バッチサイズ・文字数上限・記事数上限の制御（トークン肥大化対策）。
    - JSON Mode による厳密な JSON 出力期待と、応答の復元ロジック（前後余計テキストが混入した場合に最外側の {} を抽出して復元）を実装。
    - 429・ネットワーク断・タイムアウト・5xx を対象に指数バックオフでリトライし、その他エラーはスキップしてフェイルセーフに継続。
    - レスポンスのバリデーション（results の存在・型・既知コード・スコアの数値性）を実装。スコアは ±1.0 にクリップ。
    - 取得したスコアのみ ai_scores テーブルに置換（DELETE → INSERT）の形で冪等書き込み。部分失敗時に既存スコアを保護するため code を絞って書き換え。
    - テスト容易性のため _call_openai_api をパッチ可能にしている。
    - 公開関数: score_news(conn, target_date, api_key=None) → 書き込んだ銘柄数を返す。
  - 市場レジーム判定（regime_detector.py）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定。
    - prices_daily から MA200 比を計算する _calc_ma200_ratio（データ不足時は中立 1.0 を採用して警告ログ）。
    - raw_news からマクロキーワードでフィルタしたタイトルを抽出する _fetch_macro_news。
    - OpenAI 呼び出しは独立実装（news_nlp と内部関数を共有しない設計）。API 失敗時は macro_sentiment=0.0 にフォールバック。
    - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）と ROLLBACK の安全処理を実装。
    - 公開関数: score_regime(conn, target_date, api_key=None) → 成功時に 1 を返す。

- Research（kabusys.research）
  - ファクター計算（research/factor_research.py）
    - モメンタム（1M/3M/6M）、200日移動平均乖離、ATR（20日）、流動性（20日平均売買代金、出来高比）等を DuckDB 上の SQL と Python の組み合わせで算出する関数を実装。
    - 欠損データやデータ不足時の取り扱い（NULL / None の返却）を定義。
    - 公開関数: calc_momentum, calc_volatility, calc_value（raw_financials と prices_daily を組み合わせ）。
  - 特徴量探索（research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）: 指定ホライズン（営業日ベース）に対するリターンを一括取得する SQL 実装。horizons 引数の検証有り。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンランク相関（ランク化は同順位の平均ランクを採用）。
    - 統計サマリー（factor_summary）: count/mean/std/min/max/median を計算（None 値除外）。
    - ランク化ユーティリティ（rank）を実装（丸めで ties 対応）。
    - 研究用モジュールは外部ライブラリ（pandas 等）に依存せず標準ライブラリのみで実装する方針。

- DuckDB を中心とした DB 統合
  - 各モジュールは DuckDB 接続（duckdb.DuckDBPyConnection）を受け取り、prices_daily / raw_news / market_regime / ai_scores / raw_financials 等のテーブル操作を行う設計。
  - 各所で BEGIN/COMMIT/ROLLBACK によるトランザクション管理と例外発生時の ROLLBACK の安全処理を実装。

- ロギングと安全策
  - 各処理で詳細な logger 呼び出しを追加（info/debug/warning/exception）。
  - ルックアヘッドバイアス対策として datetime.today()/date.today() をスコアリング等の内部ロジックで直接参照しない設計を明示。
  - OpenAI 呼び出しはタイムアウトと温度固定（temperature=0）など、再現性を考慮。

### Changed
- （新規リリースのため該当なし）

### Fixed
- （新規リリースのため該当なし）

### Security
- （新規リリースのため該当なし）

### Breaking Changes
- （初回リリースのため該当なし）

---
注記:
- OpenAI の実装は openai.OpenAI クライアントを使用し、モデル gpt-4o-mini を想定しています。API キーは関数引数または環境変数 OPENAI_API_KEY から解決します。未設定時は ValueError を発生させます。
- 各モジュールの詳細な挙動（例: リトライ方針、クリップ範囲、最大記事数など）はソース内コメントに設計上の理由とともに記載されています。