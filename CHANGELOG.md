CHANGELOG
=========

すべての重要な変更をここに記録します。フォーマットは「Keep a Changelog」に準拠しています。

[0.1.0] - 2026-03-29
--------------------

Added
- 基本パッケージ初期リリースを追加。
  - パッケージ名: kabusys、バージョン: 0.1.0 (src/kabusys/__init__.py)
  - パブリックサブパッケージ: data, research, ai, execution, monitoring（__all__で公開）

- 環境設定管理機能を追加 (src/kabusys/config.py)
  - .env / .env.local ファイルおよび OS 環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルート検出機能を追加（.git または pyproject.toml を起点に探索）。
  - .env パーサを強化：export 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント取り扱い、無効行スキップに対応。
  - .env 読み込み順序: OS 環境 > .env.local(override) > .env（既存 OS 環境変数は protected として上書きされない）。
  - 自動読み込みを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを提供し、必須設定取得（_require）、デフォルト値、入力検証（KABUSYS_ENV, LOG_LEVEL）を実装。
  - 設定プロパティ群: J-Quants トークン、kabu API 設定、Slack トークン/チャンネル、DuckDB/SQLite パス、環境判定ユーティリティ（is_live/is_paper/is_dev）。

- ニュース NLP スコアリング機能を追加 (src/kabusys/ai/news_nlp.py)
  - raw_news と news_symbols を集約し銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini）でセンチメント解析。
  - JST 時間ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を計算する calc_news_window を実装。
  - バッチ処理（1 API コールあたり最大 20 銘柄）、各銘柄で記事数・文字数トリム（最大記事数/最大文字数）をサポート。
  - OpenAI の JSON Mode を利用し、厳密な JSON レスポンスを期待するプロンプト設計。
  - レート制限(429)、ネットワーク断、タイムアウト、5xx エラーに対する指数バックオフ＋リトライ実装（デフォルト上限を設定）。
  - レスポンスのバリデーションロジックを実装（JSON復元、results リスト、code/score の型検査、未知コード無視、数値チェック）。
  - スコアは ±1.0 にクリップ。部分失敗時には既存スコアを保護するため、書き込みは対象コードのみ DELETE→INSERT の置換方式。
  - テスト容易性のため、OpenAI 呼び出し部分を差し替え可能に設計（_call_openai_api を patch 可能）。

- 市場レジーム判定機能を追加 (src/kabusys/ai/regime_detector.py)
  - ETF 1321 の 200 日移動平均乖離 (ma200_ratio) とマクロニュースの LLM センチメントを合成して日次レジーム（bull/neutral/bear）を判定。
  - 合成重みは MA:70%、マクロ:30%、スケーリング・クリップ・閾値を定義。欠損時や API 失敗時の安全フォールバック（macro_sentiment=0.0）を実装。
  - DuckDB からのデータ取得はルックアヘッドバイアスを避けるため target_date 未満（排他）で取得。
  - OpenAI 呼び出しは専用の _call_openai_api を使用し、リトライ/エラーハンドリングを備える。
  - 計算結果は market_regime テーブルへ冪等的に（BEGIN / DELETE / INSERT / COMMIT）書き込み。

- リサーチ向けファクター計算・特徴量探索を追加 (src/kabusys/research/*.py)
  - calc_momentum: 1M/3M/6M リターン、200日MA乖離を計算（データ不足時は None）。
  - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。
  - calc_value: raw_financials から最新財務データを取得して PER/ROE を計算（EPS=0 等は None）。
  - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを一括 SQL で取得。
  - calc_ic / rank / factor_summary: IC（Spearman 相関）計算、ランク付け（同順位平均ランク）と統計サマリーを提供。
  - 実装は DuckDB のみを参照し、外部 API や発注機能へのアクセスは行わない旨を明記。

- データ基盤ユーティリティを追加 (src/kabusys/data/*.py)
  - calendar_management: market_calendar を用いた営業日判定、next/prev/get_trading_days、is_sq_day、JPX カレンダー夜間更新ジョブ（calendar_update_job）を実装。DB データ優先で未登録日は曜日フォールバック。バックフィル・健全性チェックあり。
  - pipeline / etl: ETLResult データクラスを提供し、ETL の差分取得／保存／品質チェックのためのインターフェースを整備。_get_max_date / _table_exists 等のユーティリティを実装。
  - etl モジュールは pipeline.ETLResult を再エクスポート。

Changed
- コード設計上の決定と安全措置:
  - いずれのモジュールも datetime.today()/date.today() を直接参照しない（外部から target_date を受け取る設計）ことでルックアヘッドバイアスを防止。
  - OpenAI への依存部分は明確に分離し、テスト時にモック可能な設計にしている（_call_openai_api の差し替え）。
  - DuckDB 固有の互換性ワークアラウンドを導入（executemany に空リストを渡さない等）。
  - DB 書き込みは可能な限り冪等に実行（DELETE→INSERT、ON CONFLICT の想定）し、部分失敗時の既存データ保護を優先。

Fixed
- フォールバックとフェイルセーフの強化:
  - OpenAI API エラー時は例外を上位に伝えず安全にフェイルバック（macro_sentiment=0.0 やスキップ）してバッチ処理を継続する箇所を多数実装。
  - JSON パース失敗時に余剰テキストが混入するケースを想定して「最外側の {} を抽出して復元」する処理を追加。

Security
- 機密情報の取り扱い:
  - 環境変数の自動上書きを防ぐため、OS 環境変数を protected セットとして .env の上書きから保護。
  - OpenAI API キーなどの必須設定は明示的に _require でチェックし、不足時は ValueError を投げる。

Notes / Implementation details
- OpenAI は gpt-4o-mini を想定し JSON Mode（response_format={"type":"json_object"}）で呼び出す設計。
- ニューススコアリングは1銘柄あたりの長文トークン肥大を避けるため記事数と文字数でトリムを実施（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
- Regime detection は ETF コード 1321 を利用して 200 日 MA ベースのマクロ指標と LLM センチメントを合成する仕様。
- calendar_update_job は J-Quants クライアント（kabusys.data.jquants_client）を想定した差分取得と保存のフローを実装。API 例外時や取得レコード無しの場合は安全に 0 を返す。

Acknowledgements / Testing hints
- OpenAI 呼び出しを含む箇所はモジュール単位で内部の _call_openai_api を unittest.mock.patch で差し替えられるように設計されています。
- DuckDB を使った統合テスト向けに、環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を使って .env 自動読み込みを無効化できます。

今後予定（推測・提案）
- ai モジュールの学習済みプロンプト微調整や追加モデルサポート。
- ETL の具体的な差分取得ロジック（J-Quants API 用 ID トークン注入やスケジューリング）と品質チェックの詳細ルール強化。
- monitoring / execution モジュールの実装拡充（現状はパッケージ公開のみの状態）。

---
この CHANGELOG はソースコードから推測して作成しています。補足や日付修正、項目の追加・削除が必要であれば指示してください。