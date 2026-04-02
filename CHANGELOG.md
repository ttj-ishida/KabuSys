CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の方針に従っています。  

0.1.0 - 2026-04-02
------------------

初回リリース。主要な機能群（設定管理、データ ETL / カレンダー管理、リサーチ用ファクター計算、AI によるニューススコアリング・市場レジーム判定）を実装しました。

Added
- パッケージ公開
  - kabusys パッケージのベースを追加。__version__ = 0.1.0、主要サブパッケージを公開（data, research, ai, などを意図）。
- 設定・環境変数管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
  - 自動ロードの探索はパッケージのファイル位置からプロジェクトルート（.git または pyproject.toml）を特定して行うため、CWD に依存しない。
  - .env のパース機能を強化：
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のエスケープ対応
    - 行内コメントの取り扱い（クォート外、直前がスペース/タブの '#' をコメントと判断）
  - 自動ロード順序: OS 環境変数 > .env.local > .env。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - Settings クラスを提供し、主要設定（J-Quants / kabuAPI / Slack / DB パス / 監視閾値 / env/log_level 判定等）のプロパティを安全に取得可能。
  - 必須環境変数未設定時に明示的なエラーを発生させる _require() を実装。
  - KABUSYS_ENV と LOG_LEVEL のバリデーションを実装（許容値チェック）。
- データプラットフォーム / カレンダー (kabusys.data.calendar_management)
  - JPX カレンダー管理ロジックを実装（market_calendar テーブル参照）。
  - 営業日判定ユーティリティを提供: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
  - DB にカレンダー情報がない場合の曜日ベースのフォールバックを実装（週末は非営業日）。
  - calendar_update_job を実装：J-Quants API から差分取得→冪等保存（fetch / save を jquants_client と連携）。
  - バックフィル・健全性チェック（未来日付の異常検出）を導入。
- ETL パイプライン基盤 (kabusys.data.pipeline, etl)
  - ETLResult データクラスを追加し、ETL 実行結果（取得数・保存数・品質問題・エラー）を表現。
  - 差分取得・バックフィル・品質チェックを行うパイプライン設計を実装（jquants_client / quality と連携する設計）。
  - ETL の互換性や DuckDB 実行時の注意（executemany の空リスト回避等）を考慮した実装。
- AI: ニュース NLP (kabusys.ai.news_nlp)
  - raw_news と news_symbols から銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）を用いて銘柄別センチメント（ai_score）を算出し ai_scores テーブルへ書き込むワークフローを実装。
  - 処理の特徴:
    - JSTベースの収集ウィンドウ計算（前日15:00〜当日08:30の扱い）。
    - 銘柄単位で記事を最新順に集約し、1銘柄あたり最大記事数・最大文字数でトリム。
    - 最大 20 銘柄ずつバッチ送信（チャンク処理）。
    - JSON Mode を用いた厳格なレスポンス検証と復元ロジック（前後に余計なテキストが混入した場合の {} 抽出対応）。
    - レート制限(429)、ネットワーク断、タイムアウト、5xx に対する指数バックオフによるリトライ実装。
    - スコアは ±1.0 にクリップ、バリデーション失敗や API 失敗時は該当チャンクをスキップしてフェイルセーフ動作。
    - DB 書込みは対象コードのみを DELETE → INSERT する方式で部分失敗時に既存スコアを保護（冪等処理）。
- AI: 市場レジーム判定 (kabusys.ai.regime_detector)
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で market_regime を判定・保存する処理を実装。
  - 特徴:
    - ma200_ratio の計算は target_date 未満のデータのみを使用してルックアヘッドバイアスを防止。
    - マクロニュースの抽出はマクロキーワードでフィルタ（最大 20 件）し、OpenAI（gpt-4o-mini）の JSON 出力をパースして macro_sentiment を取得。
    - API 失敗時は macro_sentiment=0.0 にフォールバックして処理継続（フェイルセーフ）。
    - レジームスコアの閾値に基づき "bull"/"neutral"/"bear" を判定し market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。
- 研究用ファクター計算 (kabusys.research)
  - factor_research:
    - モメンタム (1M/3M/6M)、MA200乖離、20日 ATR、20日平均売買代金、出来高比などの計算関数を実装（prices_daily / raw_financials を参照）。
    - 欠損データやデータ不足時の取り扱い（None を返す）を明示。
  - feature_exploration:
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）、IC（Spearman の ρ）計算、ランク化ユーティリティ、ファクター統計サマリーを実装。
    - 外部依存（pandas 等）を使わず標準ライブラリで完結する実装。
  - research.__init__ で主要関数を再エクスポート。
- ロギング・保護的挙動
  - 各所で詳細な logger メッセージを追加（警告・情報・デバッグ）。
  - DB 書き込み失敗時には ROLLBACK を試み、ROLLBACK 失敗時に警告ログを出す設計。

Changed
- 初期リリースのため該当なし。

Fixed
- 初期リリースのため該当なし。

Security / Requirements
- OpenAI API キー（OPENAI_API_KEY）は news_nlp / regime_detector の実行に必須。各関数は api_key 引数で注入可能。
- J-Quants 関連や kabuAPI、Slack など外部サービス用の環境変数が必要（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。必須変数未設定時は Settings が例外を投げる。
- .env 自動ロードは意図せぬ環境上書きを避けるため保護（OS 環境変数を優先）を考慮。

Notes / Design decisions
- ルックアヘッドバイアス防止: AI モジュールやファクター計算は内部で date.today() を参照せず、明示的な target_date を受け取る設計。
- API 呼び出しはフェイルセーフ（部分失敗の継続）を優先し、重要な処理は冪等に設計（DELETE→INSERT 等）。
- DuckDB に対する互換性・制約（executemany の空リスト禁止など）を考慮した実装。

今後の予定（非確定）
- monitoring / execution 等の実行系・監視系モジュールの実装・公開。
- テストカバレッジの拡充、J-Quants / kabu API クライアントの統合テスト強化。
- 高可用性・エラー通知（Slack 連携等）の追加強化。

-----