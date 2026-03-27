# Changelog

すべての注目すべき変更点を記録します。フォーマットは Keep a Changelog に準拠しています。

## [0.1.0] - 2026-03-27

初回リリース — 日本株自動売買システム「KabuSys」ライブラリのベース機能を実装。

### Added
- パッケージ公開
  - パッケージルート: kabusys（__version__ = "0.1.0"）
  - 主要サブパッケージを __all__ でエクスポート: data, strategy, execution, monitoring

- 環境設定/管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動ロードする機能を実装。
    - プロジェクトルートの自動検出: .git または pyproject.toml を基準に探索（CWD非依存）。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - 自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 強化された .env パーサ:
    - export KEY=val 形式、シングル/ダブルクォート内のエスケープ、インラインコメント処理に対応。
    - 無効行（空行やコメント）を適切にスキップ。
  - Settings クラスを提供（settings インスタンスで使用）:
    - J-Quants / kabuステーション / Slack / DB パス等のプロパティ（必須項目は未設定時に ValueError を送出）。
    - KABUSYS_ENV の検証（development / paper_trading / live）と LOG_LEVEL の検証。
    - is_live / is_paper / is_dev のユーティリティプロパティ。

- AI モジュール (kabusys.ai)
  - ニュース NLP (kabusys.ai.news_nlp)
    - score_news 関数: raw_news と news_symbols を集約して銘柄ごとのセンチメント（ai_score）を取得し ai_scores テーブルへ書き込む。
    - 時間ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST、内部は UTC naive で扱う calc_news_window）。
    - OpenAI (gpt-4o-mini) へのバッチ送信実装（バッチサイズ: 20 銘柄）。
    - 1 銘柄あたりの記事トリム（件数上限・文字数上限）や JSON Mode レスポンスの厳密検証。
    - リトライ（429/ネットワーク/タイムアウト/5xx）を指数バックオフで処理。
    - レスポンス検証失敗時は安全にスキップし、部分成功に対応する DB 更新ロジック（DELETE → INSERT）。
    - テスト用フック: _call_openai_api を patch して差し替え可能。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - score_regime 関数: ETF 1321 の 200日移動平均乖離（重み70%）とマクロセンチメント（重み30%）を合成して日次レジーム（bull/neutral/bear）を計算、market_regime テーブルへ冪等書き込み。
    - マクロニュース選別（キーワードリスト）と LLM によるセンチメント判定（gpt-4o-mini）。
    - MA不足・API障害フェイルセーフ（ma200_ratio=1.0 や macro_sentiment=0.0）を明示的に実装。
    - OpenAI API 呼び出しは独立実装でモジュール間結合を避ける。リトライ/ログを充実。

- データプラットフォーム（kabusys.data）
  - カレンダー管理 (calendar_management)
    - market_calendar を利用した営業日判定とユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB データ不足時の曜日フォールバックロジック（週末を非営業日扱い）。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新。バックフィル・健全性チェックを実装。
  - ETL / パイプライン (pipeline, etl)
    - ETLResult データクラス: ETL 実行結果の構造化保存および to_dict（品質問題をシリアライズ）を実装。
    - 差分取得・バックフィル方針・品質チェック連携の設計に対応。
    - jquants_client と quality モジュールとの連携ポイントを設計（fetch/save の呼び出し場所を想定）。

- リサーチ機能（kabusys.research）
  - factor_research モジュール
    - calc_momentum, calc_volatility, calc_value を実装。
    - Momentum: 1M/3M/6M リターンと MA200 乖離（データ不足時は None）。
    - Volatility: 20日 ATR、ATR 比率、20日平均売買代金、出来高比率。
    - Value: PER（EPS が 0 または欠損の場合 None）、ROE（raw_financials からの取得）。
    - DuckDB を用いた SQL ベース実装、結果は (date, code) をキーとする dict のリストで返却。
  - feature_exploration モジュール
    - calc_forward_returns: 任意ホライズン（既定 [1,5,21]）の将来リターン計算（複数ホライズンを1クエリで取得）。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）計算。データ不足時は None。
    - rank: 同順位は平均ランクとするランク付け実装（丸め処理で ties の誤差に対処）。
    - factor_summary: count/mean/std/min/max/median の基本統計量算出。
  - data.stats から zscore_normalize を再利用可能にエクスポート。

### Changed
- 実装上の設計思想として以下を徹底
  - datetime.today()/date.today() をスコープ内で直接参照しない（ルックアヘッドバイアス回避）。target_date パラメータベースで処理を行う。
  - DuckDB に対する互換性・安全性を重視（executemany の空リスト回避など）。
  - LLM レスポンスの堅牢なパースと部分失敗耐性（JSON 前後ノイズ復元、未知コード無視、数値検証）。
  - DB 書き込みは冪等性を意識（DELETE → INSERT、トランザクション BEGIN/COMMIT/ROLLBACK の明示）。

### Fixed
- エッジケースの安全対策とログ整備
  - .env ファイル読み込み失敗時に警告（warnings.warn）を出力し処理継続。
  - LLM レスポンスの JSON パース失敗や API エラー発生時に例外を巻き上げず、フォールバック値（0.0）で継続することでパイプライン全体の耐障害性を向上。
  - DB 書き込み失敗時に ROLLBACK を試行し、ROLLBACK 自体の失敗も警告ログで記録。

### Security
- 必須機密情報（OpenAI API Key, Slack トークン, Kabu API パスワード, J-Quants トークン等）は Settings により存在チェックを行い、未設定時は ValueError を送出して明示的に失敗するように設計。

### Notes / Implementation details
- OpenAI 関連: gpt-4o-mini を利用、JSON Mode を要求して厳密 JSON を期待する。ただし実運用でのノイズを考慮して前後テキストの補正ロジックを実装。
- テスト容易性: OpenAI 呼び出し関数（_call_openai_api）をモジュール内で分離してあり、unittest.mock.patch で差し替え可能。
- DuckDB を主要なローカルデータストアとして利用。データスキーマ（prices_daily, raw_news, ai_scores, market_regime, market_calendar, raw_financials など）を前提として処理を実装。

---

今後の予定（例）
- strategy / execution / monitoring の具体実装の追加（発注ロジック、監視アラート連携など）。
- 詳細なドキュメント（API リファレンス、使用例、デプロイ手順）とサンプルデータセット。
- ユニットテストおよび統合テスト群の追加（ETL/AI 呼び出しのモック含む）。

もし CHANGELOG の表記や日付、あるいは個別の変更点をより詳細に追記したい箇所があれば、ご指定ください。