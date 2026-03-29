All notable changes to this project will be documented in this file.

The format is based on "Keep a Changelog" and this project adheres to Semantic Versioning.

[Unreleased]

# 0.1.0 - 2026-03-29
初期公開リリース。

このリリースでは、日本株自動売買システムのコアとなるモジュール群を一通り実装して公開します。主要な機能はデータ取り込み（ETL）・マーケットカレンダー管理・ファクター算出・ニュースNLP・市場レジーム判定・環境設定管理などです。下記に主要追加点・挙動設計上のポイントやフェイルセーフ処理をまとめます。

Added
- パッケージ基盤
  - kabusys パッケージ初期版 (バージョン 0.1.0)。__all__ に data, strategy, execution, monitoring を公開。
- 環境設定・.env 管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定をロードする Settings クラスを追加。
  - 自動ロードの優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート（テスト用）。
  - .env ファイルパーサ実装: export KEY=val 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、行内コメント処理などに対応。
  - OS の既存環境変数を保護する protected キーセットにより、.env の上書きを制御。
  - 必須値チェック (JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等) は未設定時に ValueError を送出。
  - その他: DUCKDB_PATH / SQLITE_PATH / KABUSYS_ENV / LOG_LEVEL 等のデフォルトとバリデーション。
- ニュースNLP (kabusys.ai.news_nlp)
  - score_news 関数を実装。raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）で銘柄毎のセンチメントスコアを算出し ai_scores テーブルへ保存。
  - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で提供。
  - バッチ送信 (最大 20 銘柄 / リクエスト)、記事トリム（最大記事数・最大文字数）、JSON Mode を使ったレスポンス検証、数値クリップ（±1.0）を実装。
  - レスポンスの堅牢なバリデーション（JSON 抽出、results キー、コード照合、数値チェック）。
  - エラー時は該当チャンクをスキップして処理を継続（フェイルセーフ）。最終的に成功した銘柄のみを DELETE→INSERT で置換（冪等性・部分失敗耐性）。
  - テスト容易性のため _call_openai_api をモック可能に設計。
- 市場レジーム判定 (kabusys.ai.regime_detector)
  - score_regime を実装。ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次レジーム（bull/neutral/bear）を算出・保存。
  - マクロキーワードで raw_news をフィルタし、最大件数で LLM に渡す。OpenAI 呼び出しは gpt-4o-mini の JSON Mode を使用。
  - リトライ・バックオフ、API エラーの分類（5xx は再試行、非5xx はフォールバック）、JSON パース失敗時は macro_sentiment=0.0 にフォールバックして継続。
  - データベース書き込みは BEGIN / DELETE / INSERT / COMMIT で冪等化。失敗時は ROLLBACK を試行。
- 研究（リサーチ）モジュール (kabusys.research)
  - factor_research: calc_momentum, calc_value, calc_volatility を実装。prices_daily / raw_financials を利用してモメンタム・バリュー・ボラティリティ等の定量ファクターを算出。
  - feature_exploration: calc_forward_returns（任意ホライズン対応、パフォーマンスを考慮した一括クエリ）、calc_ic（Spearman ランク相関）、rank（同順位は平均ランク）、factor_summary（count/mean/std/min/max/median）を実装。
  - データの参照範囲や窓幅はパラメータ化（例: 200 日 MA、20 日 ATR 等）。
  - zscore_normalize を data.stats から再エクスポート（research/__init__）。
- データプラットフォーム周り (kabusys.data)
  - calendar_management: market_calendar を用いた営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）および calendar_update_job（J-Quants からの差分取得と保存）を実装。
    - market_calendar 未取得時の曜日ベースフォールバック（週末を非営業日扱い）。
    - DB 登録値優先、未登録日は曜日フォールバックで一貫性を保つアルゴリズム。
    - バックフィル、健全性チェック（未来日付の異常検出）を実装。
  - pipeline / etl: ETLResult データクラスを実装して ETL 実行結果を集約（取得数・保存数・品質問題・エラー等を含む）。
  - jquants_client と quality モジュールとの連携を想定した差分取得・保存・品質チェックの設計骨格を提供。
  - data.etl で pipeline.ETLResult を再エクスポート。
- DuckDB を前提とした DB 操作
  - 全モジュールで DuckDB 接続を引数に取り、SQL と Python を組み合わせて処理。executemany の空リストバインドに対する互換性対策を実装。

Changed
- （初回リリースのため該当なし）

Fixed / Behavior
- ルックアヘッドバイアス対策
  - news_nlp / regime_detector / research モジュールは datetime.today() / date.today() を内部ロジックに直接参照せず、明示的な target_date 引数に基づいて処理を行う。
  - prices_daily クエリ等で date < target_date の排他条件を利用し、将来データの参照を防止。
- フェイルセーフ設計
  - OpenAI API 呼び出し失敗時は例外を投げず中立スコア（0.0）やチャンクスキップで継続する処理を導入（重要な箇所での全体停止を回避）。
  - DB 書き込みはトランザクションで囲み、失敗時の ROLLBACK を試行。ROLLBACK 自体の失敗は警告ログで通知。
- OpenAI 統合の堅牢化
  - JSON Mode で厳密な JSON 出力を期待しつつ、前後余計なテキストが混入した場合に最外の {} を抽出して復元するフォールバックを実装。
  - RateLimit・接続断・タイムアウト・5xx を想定した指数バックオフリトライを複数箇所で実装。
- .env パーサの堅牢化
  - export プレフィックス対応、クォート内エスケープ処理、行内コメントの取り扱い、不正行の無視などを実装。
  - プロジェクトルート検出は __file__ を起点に親ディレクトリから .git または pyproject.toml を探す実装で、パッケージ配布後も動作するよう配慮。

Security
- API キーの取り扱い
  - OpenAI 等の API キーは引数か環境変数（OPENAI_API_KEY など）で渡す設計。未設定時は ValueError を送出して明示的に要求。
  - .env の自動ロードはデフォルトで有効だが、テスト時には KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。
  - OS 環境変数を保護する仕組み（protected set）を導入し、.env による既存環境変数の上書きを防止。

Notes / Implementation details
- OpenAI モデルは gpt-4o-mini を想定して実装。messages + JSON Mode を用いる設計。
- DuckDB のバージョン差異に配慮した実装（例: executemany の空リスト回避、ANY(?) の不安定さを回避するための個別 DELETE 処理）。
- テスト支援のため内部の _call_openai_api を unittest.mock.patch で差し替えられるようにしている箇所がある。
- ロギングを広く配置し、処理の進捗・警告・例外を可読に記録する方針。

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- （初回リリースのため追加のセキュリティ修正はなし）

今後の予定（参考）
- ai モジュールの追加ユースケース（ニュース要約や銘柄レベルの詳細分析など）。
- ETL の具体的実装（jquants_client, quality の詳細接続・テストケース追加）。
- Strategy / execution / monitoring モジュールの実装・統合テスト（現在はパッケージ名で公開のみ）。
- ドキュメント・利用ガイドと例（環境構築、サンプル ETL 実行、AI キー設定方法等）。

---

この CHANGELOG はコードベース（ソース内の docstring コメントや関数実装、設計注釈）から推測して作成しています。リポジトリ上のコミット履歴に基づく厳密な変更履歴が必要な場合は、実際のコミットログを参照して差分を反映してください。