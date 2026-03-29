CHANGELOG
=========

すべての重要な変更をここに記載します。フォーマットは「Keep a Changelog」に準拠しています。

[Unreleased]
------------

なし

[0.1.0] - 2026-03-29
--------------------

Added
- パッケージ初版リリース。モジュール構成:
  - kabusys.config: 環境変数/設定管理（.env 自動読み込み、.env.local 優先、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化）。
    - .env 解析で export プレフィクス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理（クォート有り/無しの差分処理）を実装。
    - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 実行環境（development, paper_trading, live）/ログレベル等を環境変数から取得。必須変数未設定時は明確なエラーメッセージを送出。
  - kabusys.ai.news_nlp: ニュースを LLM（gpt-4o-mini）でセンチメント評価し ai_scores に書き込む機能を実装。
    - ニュース収集ウィンドウ計算（JST ベース→UTC naive datetime で返却）。
    - 銘柄ごとに記事を集約し（最大記事数・文字数でトリム）、最大 20 銘柄単位でバッチ送信。
    - JSON Mode を利用した厳格なレスポンス検証、部分的失敗時のフォールバック（失敗銘柄のみスキップ）、スコアを ±1.0 にクリップ。
    - ネットワーク・429・タイムアウト・5xx に対する指数バックオフリトライ実装。
    - テスト容易性のため OpenAI 呼び出し点（_call_openai_api）をモック差し替え可能に設計。
  - kabusys.ai.regime_detector: ETF (1321) の200日移動平均乖離とマクロニュースの LLM センチメントを合成して日次市場レジーム（bull/neutral/bear）判定を実装。
    - ma200_ratio 計算（ルックアヘッドバイアス防止のため target_date 未満のデータのみ参照）。
    - マクロキーワードで raw_news をフィルタし、LLM により macro_sentiment を取得（API失敗時は 0.0 フォールバック）。
    - 重み付け合成（70%:MA、30%:マクロ）と閾値に基づくラベル付け、market_regime へ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。
  - kabusys.research: ファクター計算・特徴量探索機能を実装。
    - factor_research.calc_momentum / calc_volatility / calc_value: モメンタム（1M/3M/6M、MA200乖離）、ATR/流動性指標、PER/ROE 等を DuckDB の prices_daily / raw_financials から算出。
    - feature_exploration.calc_forward_returns / calc_ic / rank / factor_summary: 将来リターン計算、Spearman（ランク）による IC 計算、ランク化ユーティリティ、基本統計サマリー。いずれも外部ライブラリに依存せず標準ライブラリのみで実装。
    - 出力は (date, code) をキーとする辞書リストとして返却。
  - kabusys.data:
    - calendar_management: JPX カレンダーの夜間更新ジョブ（J-Quants 経由）と営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。market_calendar 未取得時は曜日ベースのフォールバックを使用。
    - pipeline.ETLResult: ETL の実行結果を表すデータクラス（品質問題・エラー集約、to_dict による整形を提供）。
    - pipeline: ETL パイプラインの基礎ロジック（差分取得、バックフィル、品質チェックの呼び出し方針、idempotent 保存の方針）を実装。
    - etl から ETLResult を公開再エクスポート。
  - 共通ユーティリティ:
    - DuckDB 関連の互換性考慮（executemany に空リスト不可等）や日付変換ユーティリティを多数実装。
    - 詳細なロギングを各処理に追加。

Changed
- 初版リリースのため変更履歴なし（新規追加）。

Fixed
- レスポンスパース失敗や API エラーでプロセスが例外で停止しないように多くのフェイルセーフを追加:
  - OpenAI 呼び出し失敗時は警告ログを出力して安全なデフォルト（0.0 等）へフォールバックする実装。
  - DuckDB のトランザクションで例外発生時に ROLLBACK を試行し、ROLLBACK 自体が失敗した場合は警告を出力して上位へ例外を伝播。

Security
- 環境変数の扱いに注意（重要なトークンは Settings で必須としており、未設定時に明示的なエラーを出す）。

Removed / Deprecated
- なし

Notable design decisions / implementation notes
- ルックアヘッドバイアス防止: 各 AI / 研究処理で datetime.today() / date.today() を参照せず、引数で与えられた target_date を基準としてデータ選択を行う設計。
- テスト容易性: OpenAI 呼び出し箇所は内部関数で切り出し、unittest.mock.patch により置換可能。
- 部分失敗許容: API の一部失敗があっても他の銘柄・処理を保護するため、DB 書き込みでは対象コードを絞って削除→挿入する方式を採用。
- DuckDB 互換性を考慮した実装（空配列バインド回避など）。

今後の予定（例）
- ai スコアの履歴・品質分析機能強化
- ETL ワークフローの細分化および監査ログ追加
- 単体テスト・統合テストの追加と CI パイプライン整備

--- 

注: 本 CHANGELOG は提示されたコードベースの実装内容に基づき推測して作成した初回リリース向けの記述です。