# Changelog

すべての変更は Keep a Changelog の形式に従っています。  
タグ付けは semver を想定しています。

現在日付: 2026-03-28

## [Unreleased]

## [0.1.0] - 2026-03-28
初回リリース。日本株自動売買プラットフォームのコアライブラリを提供します。主な機能・変更点は以下の通りです。

### 追加
- パッケージ初期化
  - kabusys パッケージの公開APIを定義（data, strategy, execution, monitoring）。
  - バージョン: 0.1.0

- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込むユーティリティ実装。
  - プロジェクトルート自動検出ロジック（.git または pyproject.toml を起点）。
  - .env のパース機能を実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応）。
  - 自動読み込みの優先順位を実装（OS 環境変数 > .env.local > .env）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス等の設定プロパティを公開。
  - env / log_level の値検証（許容値チェック）とブール判定ユーティリティ（is_live / is_paper / is_dev）。

- ニュースNLP（kabusys.ai.news_nlp）
  - raw_news, news_symbols を用いて銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）の JSON Mode でセンチメントスコアを取得。
  - タイムウィンドウ計算（JST 基準: 前日 15:00 ～ 当日 08:30）を実装（calc_news_window）。
  - バッチ処理（1回あたり最大 20 銘柄）、記事トリム（最大記事数・最大文字数）によるトークン肥大化対策を実装。
  - 再試行（429 / ネットワーク断 / タイムアウト / 5xx）をエクスポネンシャルバックオフで実装。
  - レスポンスのバリデーション（JSON 抽出、構造チェック、スコアのクリップ）を実装。
  - DuckDB への冪等書き込み（対象コードのみ DELETE → INSERT）を実装。
  - score_news API を公開（DuckDB 接続と target_date を受け取り、書き込んだ銘柄数を返す）。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を組み合わせて日次レジーム判定を実装。
  - ma200_ratio の計算（ルックアヘッド防止のため target_date 未満のみ使用）とデータ不足時のフォールバック。
  - マクロ記事抽出（マクロキーワードによるフィルタ）と OpenAI 呼び出し（gpt-4o-mini）による macro_sentiment 評価。
  - API エラー・パース失敗時は macro_sentiment=0.0 でフェイルセーフ継続（例外を投げない）。
  - 合成スコアのクリップとラベル付け（bull / neutral / bear）。
  - market_regime テーブルへの冪等な書き込み（BEGIN / DELETE / INSERT / COMMIT）。
  - score_regime API を公開（DuckDB 接続と target_date を受け取り成功時に 1 を返す）。

- データプラットフォーム（kabusys.data.*）
  - カレンダー管理（calendar_management）
    - market_calendar を使った営業日判定（is_trading_day）と SQ 日判定（is_sq_day）。
    - next_trading_day / prev_trading_day / get_trading_days を実装（DB 優先、未登録日は曜日ベースでフォールバック）。
    - 夜間バッチ更新 job（calendar_update_job）を実装：J-Quants から差分取得・バックフィル・健全性チェック・保存を行う。
    - DB 未取得時の曜日フォールバック、探索上限（日数）による安全策を実装。
  - ETL パイプライン（pipeline）
    - ETLResult データクラスを実装（取得件数・保存件数・品質問題リスト・エラー集約など）。
    - _table_exists / _get_max_date 等のユーティリティを実装。
  - etl モジュールの公開インターフェース（ETLResult の再エクスポート）。

- 研究系（kabusys.research.*）
  - ファクター計算（factor_research）
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、バリュー（PER/ROE）、流動性指標を DuckDB 上で計算する関数を実装。
    - データ不足時の None ハンドリング、営業日スキャン上のバッファ実装。
  - 特徴量探索（feature_exploration）
    - 将来リターン計算（calc_forward_returns、任意ホライズン対応）、IC（Spearman）計算、ランク変換（rank）、統計サマリー（factor_summary）を実装。
    - pandas 等外部依存を使わず、標準ライブラリと DuckDB SQL で実装。
  - z-score 正規化ユーティリティを data.stats から公開。

### 変更（設計上の重要な決定 / 改良）
- ルックアヘッドバイアス防止
  - AI モジュール（news_nlp, regime_detector）や研究系関数は内部で datetime.today()/date.today() を直接参照しない設計。必ず target_date を明示的に受け取ることで未来データ参照を防ぐ。
  - DB クエリは target_date 未満または target_date といった排他/包含条件を明示している。

- フェイルセーフ性の強化
  - OpenAI API 呼び出しにおける多数の失敗ケース（RateLimit/IP/TLS/5xx/パース不良）に対して、適切にログ出力してスコアを 0.0 または空スコアとして継続する設計。ETL やスコアリング処理が単一失敗で全体停止しないようにした。

- DuckDB 互換性考慮
  - executemany に空リストを渡せない制約を考慮して、書き込み前に空チェックを行う実装（部分失敗時の既存スコア保護のための個別 DELETE → INSERT の採用など）。

### 修正（バグ修正 / 回避策）
- .env パーサ
  - export プレフィックス、クォート内のエスケープシーケンス、インラインコメントの扱いなど、実運用で多発しうる .env 書式の取りこぼしを修正・強化。
  - ファイル読み込み失敗時は警告を出して継続（プロセス停止を避ける）。

- OpenAI 呼び出しの堅牢化
  - JSON モードでも前後に余分なテキストが混入する場合を想定し、最外側の {} を抽出してパースする復元ロジックを追加。
  - APIError の status_code の有無に依存しない安全な扱いを実装。

- カレンダー & 日付ロジック
  - market_calendar が未取得/一部のみ登録されている場合でも next/prev/get_trading_days が一貫した結果を返すように修正（DB 優先、未登録は曜日フォールバック）。
  - calendar_update_job に健全性チェック（将来日付の異常検出）とバックフィルを追加。

### 既知の制限 / 注意点
- OpenAI 依存
  - news_nlp, regime_detector は OpenAI API（gpt-4o-mini）を前提としている。API キー未設定時は ValueError を返す。
  - LLM の振る舞い次第でレスポンスのフォーマットが崩れる可能性があり、その場合は当該チャンクをスキップして継続するフェイルセーフ動作となる。

- DuckDB スキーマ依存
  - 多くの処理は prices_daily, raw_news, news_symbols, ai_scores, market_calendar, raw_financials 等のスキーマ存在を前提とする（ETL 初期化が別途必要）。

- 部分的トランザクション設計
  - ai_scores / market_regime への書き込みは対象コードのみを置換することで部分失敗時に既存データを保護する設計。ただし完全なロールフォワード保証（複数テーブルをまたぐ原子的更新）は提供していない。

### ドキュメント / テスト関連
- 各モジュールに docstring と設計方針を詳細に記載。テスト用に OpenAI 呼び出し箇所を monkeypatch / patch できるよう明示（ユニットテスト容易化を考慮）。

---

今後の予定（例）
- strategy / execution / monitoring の具体実装と CI / 自動テスト整備
- ai モデルの切替え可能化（プロンプト最適化、モデルプラガブル化）
- ETL のジョブ化（スケジューリング、監視、リトライポリシー強化）
- ドキュメントの整備（使用例・DB スキーマ定義・運用手順）

もし CHANGELOG に追記してほしい点（リリース日付、より詳細な修正履歴、特定ファイルの変更点など）があれば教えてください。