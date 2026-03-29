# Changelog

すべての公開変更は Keep a Changelog の形式に従って記載しています。  
このファイルはコードベースからの実装内容を元に推測して作成したリリースノートです。

フォーマット:
- 変更はセクション (Added / Changed / Fixed / Deprecated / Removed / Security) ごとに分類しています。
- 日付はこの CHANGELOG を生成した日付です。

## [Unreleased]

- 今後の改善候補（実装済みコードから推測）
  - OpenAI API 呼び出しのモック/テストヘルパーを公開 API として整備
  - ETL の差分計算や品質チェック結果の外部可視化（ダッシュボード連携）
  - 更なる DuckDB 互換性テスト・パフォーマンス最適化
  - 外部依存（OpenAI, J-Quants クライアント）の接続／リトライポリシーの設定化

---

## [0.1.0] - 2026-03-29

### Added
- パッケージ初期バージョンを公開
  - パッケージ名: kabusys、バージョン: 0.1.0

- 設定 / 環境変数読み込み
  - .env/.env.local からの自動読み込み機能を実装（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
  - .env の行パーサを独自実装し、`export KEY=val`、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメントの扱い等をサポート
  - OS 環境変数を保護する機構（protected set）を導入し、.env.local による上書きを制御
  - Settings クラス提供（J-Quants / kabuAPI / Slack / DB パス / 環境種別・ログレベル判定・is_live 等）

- データ基盤 (data)
  - ETL パイプラインの結果表現 ETLResult を提供（取得/保存件数、品質問題、エラー情報を保持）
  - calendar_management モジュール
    - JPX（J-Quants）カレンダー差分取得ジョブ (calendar_update_job)
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ユーティリティ
    - カレンダーデータがない場合の曜日ベースのフォールバック、最大探索日数による安全措置
  - ETL モジュール（pipeline）
    - 差分更新、バックフィル、品質チェックのためのユーティリティを実装
    - DuckDB のテーブル存在チェックや最大日付取得ユーティリティ

- 研究用ユーティリティ (research)
  - factor_research
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金・出来高比率）、バリューファクター（PER, ROE）を DuckDB クエリで実装
    - データ不足時は None を返す安全設計
  - feature_exploration
    - 将来リターン計算(calc_forward_returns)、IC（Spearman）計算(calc_ic)、ランク化ユーティリティ(rank)、ファクター統計サマリ(factor_summary)を実装
    - pandas 等に依存せず標準ライブラリと DuckDB のみで実装

- AI / ニュース分析 (ai)
  - news_nlp モジュール
    - raw_news と news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini, JSON Mode）でセンチメントを算出
    - バッチ処理（最大 20 銘柄 / チャンク）、1銘柄あたりの記事数・文字数制限、レスポンス検証ロジックを実装
    - スコアは ±1.0 にクリップし、ai_scores テーブルへ冪等的に保存
    - 429/ネットワーク断/タイムアウト/5xx に対するエクスポネンシャルバックオフの再試行実装
    - JSON パース失敗時の復元（文字列中の最外側 {} を抽出）や不正レスポンスの安全無視を実装
  - regime_detector モジュール
    - ETF(1321) の 200 日移動平均乖離（重み 70%）と、news_nlp によるマクロセンチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次判定
    - LLM 呼び出しは gpt-4o-mini（JSON Mode）を利用、リトライ/フォールバックロジック実装（失敗時 macro_sentiment=0.0）
    - レジーム判定結果を market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）
    - ルックアヘッドバイアス対策として datetime.today()/date.today() を参照せず、クエリは target_date 未満条件などで実装

- ロギング・エラーハンドリング
  - 各モジュールで警告・例外時に詳細ログを出力
  - DB 書き込みに失敗した場合は ROLLBACK を試行し、ロールバック失敗時にも警告

### Changed
- （初期リリースに含まれる堅牢化設計）
  - DuckDB のバージョン差異に対する互換性を考慮し、executemany に空リストを渡さないガードを導入（DuckDB 0.10 対応）
  - OpenAI API 呼び出し部分をモジュール内で独立実装し、テスト時に patch で差し替え可能に設計（モジュール間のプライベート関数共有を避ける）

### Fixed
- API 呼び出し・レスポンス周りの堅牢性強化
  - OpenAI の RateLimit / ネットワーク断 / タイムアウト / 5xx エラーに対し再試行（指数バックオフ）、最終的に失敗してもフェイルセーフなデフォルト（ゼロスコア）で継続する実装
  - JSON レスポンスのパース失敗を想定した復元ロジック（最外層の {} を抽出）で、稀なモードの誤差に耐性を追加
  - LLM が返す code を数値で返すなどの形式揺れに対応するため、code を str に正規化して検証
  - DuckDB からの日付値を安定して date オブジェクトに変換するユーティリティを導入

### Security
- 環境変数読み込みにおける保護機構を実装（OS 環境変数上書きを制御）
- API キーは引数注入または環境変数 OPENAI_API_KEY を要求。未設定時は ValueError を送出して安全に失敗

### Notes / その他
- 日付の取り扱いはすべて date / naive datetime（UTC 前提）で統一し、timezone の混入を避ける設計を採用
- 多くの関数はルックアヘッドバイアスを避けるため内部で日時を固定せず、必ず引数で target_date を受け取る設計
- コードはテスト容易性を意識していて、OpenAI 呼び出しや一部の副作用を patch/モックできるようになっている

---

（注）この CHANGELOG はコード内容からの推測に基づく自動作成ドキュメントです。実際の変更履歴（コミットログ、リリースノート）が存在する場合はそちらを優先してください。