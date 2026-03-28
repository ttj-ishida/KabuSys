CHANGELOG
=========

すべての注目すべき変更点をこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣例に従います。  

[Unreleased]
------------

- （該当なし）

[0.1.0] - 2026-03-28
--------------------

追加 (Added)
- 基本パッケージとエントリポイント
  - パッケージ初期バージョンをリリース。バージョンは __version__ = "0.1.0"。
  - パッケージ公開時に外部から参照されるモジュールを __all__ で公開: data, strategy, execution, monitoring（strategy/execution/monitoring の実装は別途）。
- 環境設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能を実装。プロジェクトルートは .git または pyproject.toml を基準に探索し、CWD に依存しない実装。
  - export KEY=val 形式やシングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント取り扱いなど現実的な .env 形式をパースするロジックを実装。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト向け）。
  - 環境変数取得のヘルパー Settings を提供（J-Quants / kabuステーション / Slack / DB パス / システム設定等）。
  - 環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL の許容値チェック）と is_live/is_paper/is_dev ユーティリティを実装。
  - OS 環境変数を保護する protected パラメータを用いた .env 上書き処理。
- データ処理 (kabusys.data)
  - ETL パイプラインの公開型 ETLResult を実装（pipeline.ETLResult を data.etl で再エクスポート）。
  - pipeline モジュールで差分取得・保存・品質チェックのためのユーティリティを実装。DuckDB を用いる設計。
  - 市場カレンダー管理モジュール calendar_management を追加。JPX カレンダーの夜間更新ジョブ（calendar_update_job）や営業日判定ユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を提供。
    - カレンダーが未取得の場合は曜日ベースでフォールバックする堅牢な設計。
    - 更新処理はバックフィルや健全性チェック（未来日付が大きすぎる場合のスキップ）を含む。
- 研究用分析ツール (kabusys.research)
  - ファクター計算モジュール factor_research を提供:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）。
    - calc_volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比率等。
    - calc_value: PER / ROE（raw_financials と prices_daily の組合せ）。
    - 実装は DuckDB 上の SQL を主体とした設計で、外部 API や発注処理を行わない。
  - feature_exploration モジュールを提供:
    - calc_forward_returns: 将来リターン計算（任意ホライズン）。
    - calc_ic: スピアマンのランク相関（IC）計算。
    - factor_summary: カラム別統計の算出（count/mean/std/min/max/median）。
    - rank: 同順位は平均ランクで処理するランク変換ユーティリティ。
  - 研究用ユーティリティ zscore_normalize を data.stats から再エクスポート（__init__ にて）。
- AI / ニュース解析 (kabusys.ai)
  - news_nlp モジュール:
    - raw_news と news_symbols を集約し、銘柄ごとにニューステキストを結合して OpenAI（gpt-4o-mini）で一括スコアリング。
    - JSON Mode による厳密な出力期待、レスポンス検証、数値化・±1.0 クリップ、結果を ai_scores テーブルへ冪等的に書き込む（DELETE → INSERT）。
    - バッチ処理（1 API コールあたり最大 20 銘柄）、トークン肥大化対策（記事数・文字数制限）、エクスポネンシャルバックオフによるリトライ（429/ネットワーク/タイムアウト/5xx）。
    - レスポンスの堅牢なパース（JSON 抜き出し等）と部分失敗に対する保護（書き込み対象コードを限定）。
    - calc_news_window: JST ベースのニュース時間ウィンドウ計算を提供（ルックアヘッドバイアス回避のため UTC naive datetime を返す）。
    - テスト容易性のため _call_openai_api を patch 可能に実装。
  - regime_detector モジュール:
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）と news_nlp によるマクロセンチメント（重み30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - OpenAI 呼び出しは専用実装で行い、API 失敗時は macro_sentiment=0.0 のフェイルセーフを採用。
    - 計算結果を market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - API リトライや JSON パースエラー時のログとフォールバックを実装。
- テスト・運用を考慮した設計
  - ルックアヘッドバイアスを避けるため、datetime.today() / date.today() の不使用方針を各AI・研究モジュールで徹底。
  - DuckDB の executemany の挙動差異を考慮し、空リストバインドを避ける安全な書き込み処理を実装。
  - OpenAI 呼び出し周りはエラー分類（RateLimitError, APIConnectionError, APITimeoutError, APIError）に基づくリトライ/フォールバックを実装。
  - 内部で利用する小さなヘルパー関数（例: _call_openai_api）をテスト用に差し替え可能に設計。

変更 (Changed)
- 初回リリースのため該当なし。

修正 (Fixed)
- 初回リリースのため該当なし（実装時点でのフェイルセーフやログを多めに追加）。

既知の注意点 (Notes)
- OpenAI API キーは関数引数で注入可能（api_key）で、未指定時は環境変数 OPENAI_API_KEY を参照します。キー未設定時は ValueError を送出して明示的に失敗します。
- カレンダー・価格データ等は DuckDB に保存する想定。テーブルスキーマや初期ロードは別途ドキュメント/スクリプトを参照してください。
- strategy / execution / monitoring パッケージは __all__ に含まれますが、本差分では詳細実装が別途存在するか将来追加される想定です。

今後の予定 (Unreleased ideas)
- strategy / execution / monitoring の具象実装と E2E テスト
- ai モジュールのローカルモックサーバーやオフライン評価モード追加
- CI 上での DuckDB スキーマ初期化用ユーティリティとサンプルデータ

補遺
- 本 CHANGELOG はコードから推測して作成しています。実装の微細な変更や追加ドキュメントはリポジトリの履歴・コミットログを参照してください。