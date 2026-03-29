# Changelog

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の規約に従って管理しています。  
フォーマット: https://keepachangelog.com/ja/

※この CHANGELOG はソースコードから推測して作成しています。実際の変更履歴に合わせて適宜調整してください。

## [Unreleased]

（現在のコードベースは初期リリース相当の状態としてまとめられているため、Unreleased に追記がある場合はここに記載してください。）

---

## [0.1.0] - 2026-03-29

初回公開リリース。主に以下の機能・モジュールを追加しました。

### Added
- パッケージ基本情報
  - kabusys パッケージ追加（__version__ = 0.1.0）
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ でエクスポート。

- 環境設定管理（kabusys.config）
  - .env / .env.local の自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - .env パーサ実装（export 形式、クォート／エスケープ、インラインコメント処理をサポート）。
  - 読み込み時の上書き制御（override, protected）を実装し OS 環境変数を保護。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化サポート。
  - Settings クラスを提供し環境変数から設定値を取得（検証付き）。
    - J-Quants / kabu ステーション / Slack / DB パス / 環境（development/paper_trading/live）/ログレベル等。
    - 必須項目未設定時は ValueError を発生。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（calendar_management）
    - JPX カレンダーの夜間差分更新ジョブ（calendar_update_job）。
    - 営業日判定ユーティリティ群: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB 登録値優先、未登録日は曜日ベースでフォールバック。最大探索日数の保護。
    - J-Quants クライアントを介したフェッチ/保存フロー連携（jquants_client を使用）。
  - ETL パイプライン（pipeline）
    - 差分更新・バックフィル・品質チェックの設計に基づく ETLResult データクラスを提供。
    - _table_exists / _get_max_date などの内部ユーティリティ。
  - etl モジュールは ETLResult を再エクスポート。

- AI（kabusys.ai）
  - ニュース NLP（news_nlp）
    - raw_news / news_symbols から銘柄別に記事を集約し、OpenAI（gpt-4o-mini）を用いてセンチメントスコアを生成。
    - 時間ウィンドウ計算（calc_news_window）：前日 15:00 JST ～ 当日 08:30 JST（UTC 変換あり）。
    - バッチ送信（最大 20 銘柄 / チャンク）、各銘柄のテキスト結合・トリム（文字数上限と記事数上限）。
    - JSON Mode を使ったレスポンス検証ロジック（_validate_and_extract）。不正レスポンス時は安全にスキップ。
    - リトライ戦略（429 / ネットワーク / タイムアウト / 5xx に対する指数バックオフ）。
    - 書き込みは部分失敗を許容する idempotent な操作（対象コードのみ DELETE → INSERT）。
    - 公開 API: score_news(conn, target_date, api_key=None)
  - 市場レジーム判定（regime_detector）
    - ETF 1321 の 200 日移動平均乖離（70%）とマクロニュースの LLM センチメント（30%）を合成して日次レジーム判定（bull/neutral/bear）。
    - MA200 比率計算（_calc_ma200_ratio）: ルックアヘッド防止のため target_date 未満のデータのみ使用。
    - マクロ記事抽出（_fetch_macro_news）: マクロキーワードでフィルタ。
    - OpenAI 呼び出し（_score_macro）: リトライ・フェイルセーフ（失敗時 macro_sentiment=0.0）。
    - 結果は market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - 公開 API: score_regime(conn, target_date, api_key=None)

- リサーチ（kabusys.research）
  - ファクター計算（factor_research）
    - モメンタム: mom_1m, mom_3m, mom_6m, ma200_dev（ma200 は 200 日）
    - ボラティリティ/流動性: atr_20, atr_pct, avg_turnover, volume_ratio（20日ベース）
    - バリュー: per, roe（raw_financials からの最新財務データを使用）
    - 全関数は DuckDB 接続を受け取り prices_daily / raw_financials を参照。結果は dict リストで返却。
  - 特徴量探索（feature_exploration）
    - 将来リターン計算（calc_forward_returns）: 指定ホライズン（デフォルト [1,5,21]）の fwd_* を返す。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンランク相関による評価。十分な有効レコードがない場合は None。
    - ランク変換ユーティリティ（rank）: 同順位は平均ランク、丸めで ties 対策。
    - 統計サマリー（factor_summary）: count/mean/std/min/max/median を計算。
  - research パッケージは主要関数を __all__ で再エクスポート（zscore_normalize は data.stats から参照）。

### Changed
- （初回リリースのため「変更」はありませんが、各モジュールに実装方針・設計上の注意点をコメントで明記）
  - 例: ルックアヘッドバイアス対策として datetime.today()/date.today() の直接参照を避ける旨を各 AI/研究モジュールで採用。

### Fixed
- （初版のため特定のバグ修正履歴は記載なし）

### Notes / 実装上の重要な設計判断
- OpenAI（gpt-4o-mini）利用に関するフェイルセーフ:
  - API 失敗時は例外を上位に上げず安全なデフォルト（0.0 やスキップ）で継続する設計。これにより ETL やスコア生成の一部失敗が全体停止を招かない。
- DuckDB をデータソースに想定:
  - 多くの処理が DuckDB 接続を引数に取り SQL で完結する設計。外部サービスへは直接アクセスしない（テスト容易性・安全性）。
- DB 書き込みは冪等性を重視:
  - DELETE → INSERT のパターンや ON CONFLICT を想定した保存で部分失敗時のデータ保護を実装。
- .env 読み込みはプロジェクトルート探索ベース:
  - 配布後の実行やテストのため CWD に依存しない実装。
- API キーの注入性:
  - score_news / score_regime 等は api_key 引数を受け取りテスト時に環境変数に依存せずに実行可能。

---

今後のリリース案（例）
- Unreleased:
  - strategy / execution / monitoring の実装（現時点ではパッケージエクスポートのみ）。
  - テストカバレッジ追加、型注釈の厳密化、CI ワークフロー整備。
  - ロギングやメトリクス出力の強化（Prometheus / structured logging 等）。

（この CHANGELOG はコードの実際のコミット履歴に基づくものではなく、提供されたソースコードから推測して作成した初期リリース記録です。）