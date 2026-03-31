# CHANGELOG

すべての変更は Keep a Changelog の規約に従って記載します。  
このプロジェクトはセマンティックバージョニングを使用します。

## [Unreleased]

（現時点で未リリースの変更はありません）

---

## [0.1.0] - 2026-03-31

初回リリース。日本株自動売買システム「KabuSys」の基礎コンポーネント群を実装しました。主な追加点は以下の通りです。

### Added
- パッケージ初期化
  - kabusys パッケージ（バージョン 0.1.0）を導入。公開 API: data, strategy, execution, monitoring。

- 環境設定/ローダー (kabusys.config)
  - .env および .env.local の自動読み込み機能（OS 環境変数優先・.env.local は上書き）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - .git または pyproject.toml を基準にプロジェクトルートを探索して .env を探す実装（CWD に依存しない）。
  - シンプルかつ堅牢な .env パーサ（export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理などに対応）。
  - 環境変数必須チェック用の _require ユーティリティ。
  - Settings クラス: J-Quants、kabuステーション、Slack、DB パス、監視閾値、環境/ログレベル検証などのプロパティを提供（値検証とデフォルト／型変換を含む）。

- AI（自然言語処理）モジュール (kabusys.ai)
  - news_nlp.score_news
    - raw_news と news_symbols から銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを評価して ai_scores テーブルへ書き込む。
    - バッチ処理（最大 20 銘柄/チャンク）、1 銘柄あたり記事数・文字数のトリム制御、JSON Mode を用いた応答バリデーションを実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフによるリトライ、レスポンス検証、スコアの ±1.0 クリップ。
    - 失敗時はフェイルセーフで個別チャンクをスキップし、部分失敗でも既存スコアを保護するために書き込み対象コードを限定して DELETE → INSERT で置換。

  - regime_detector.score_regime
    - ETF (1321) の 200 日移動平均乖離（70% 重み）と、マクロニュースの LLM センチメント（30% 重み）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
    - prices_daily と raw_news を参照。マクロニュースがない/API エラー時は macro_sentiment=0.0 で継続。
    - OpenAI 呼び出しは内部で OpenAI クライアントを生成し、リトライ・バックオフ・エラー分類を実装。
    - ルックアヘッドバイアス回避のため target_date 未満のみを参照する設計。

- Research（因子・特徴量）モジュール (kabusys.research)
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離率（ma200_dev）を計算。
    - calc_volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金（avg_turnover）、出来高比（volume_ratio）を計算。
    - calc_value: raw_financials と当日の株価を組み合わせて PER / ROE を計算（EPS 欠損や 0 の扱いに注意）。
    - 全関数は DuckDB の prices_daily/raw_financials のみ参照し、副作用なしで (date, code) ベースの辞書リストを返す。
  - feature_exploration
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得。
    - calc_ic: ファクター値と将来リターンのスピアマン順位相関（IC）を計算（有効データが 3 件未満の場合は None）。
    - rank: 値を平均ランクに変換（同順位は平均ランク、丸め処理で ties を安定化）。
    - factor_summary: 指定カラムの count/mean/std/min/max/median を計算。
    - いずれも外部ライブラリに依存せず標準ライブラリのみで実装。

- Data（データ基盤）モジュール (kabusys.data)
  - calendar_management
    - JPX マーケットカレンダー管理: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定 API を実装。
    - market_calendar が未取得時の曜日ベースのフォールバック（週末は非営業日）。
    - night batch job: calendar_update_job による J-Quants からの差分取得と冪等保存（バックフィル、健全性チェックを含む）。
    - DB の部分的な登録（まばらなデータ）でも next/prev/get の挙動が一貫するよう設計。
  - pipeline & etl
    - ETLResult データクラスを公開（kabusys.data.etl で再エクスポート）。
    - ETL パイプラインの基礎実装（差分取得、保存、品質チェックの統合方針を含む）を含む骨組み（jquants_client, quality モジュールとの連携を想定）。
    - DuckDB テーブル存在チェック、最大日付取得などのユーティリティを実装。

- DuckDB をデータバックエンドに利用
  - 各モジュールは DuckDB 接続を受け取り、SQL と Python を組み合わせて処理を行う設計。

- ロギングとエラーハンドリング
  - 各処理は詳細なログを出力（INFO/DEBUG/WARNING/exception）。
  - OpenAI / 外部 API 呼び出しはリトライやフォールバックを実装し、例外でプロセス全体が停止しないように設計。

### Changed
- （初回リリースのため「Changed」は特になし）

### Fixed
- （初回リリースのため「Fixed」は特になし）

### Security
- OpenAI API キーや Slack トークンなどの機密情報は環境変数経由で読み取る設計。Settings クラスは必須キー未設定時に ValueError を発生させるため、運用時は環境変数管理に注意してください。

### Notes / 設計上の注意点
- ルックアヘッドバイアス防止のため、score_news / score_regime 等の関数は内部で datetime.today() / date.today() を参照せず、必ず呼び出し側から target_date を受け取る設計です。
- DuckDB のバージョン差異（executemany の空リストの扱い、リスト型バインドの挙動など）に配慮した実装を行っています。
- OpenAI 呼び出しは JSON mode を利用しつつ、返却の冗長テキストや不正フォーマットに対する耐性（{} 抽出・パースの保護）を実装しています。
- idempotent な DB 書き込み（DELETE → INSERT、ON CONFLICT 想定）で部分失敗時のデータ保護を行っています。

---

今後の予定（例）
- strategy / execution / monitoring の具現化（発注ロジック、実行中モニタリング、PID 管理など）の追加実装。
- jquants_client および quality モジュールの具体実装と統合テスト。
- ユニットテスト・統合テストの整備、CI ワークフローの導入。

（上記はコードから推測してまとめた初回リリース向けのCHANGELOGです。実際のリリースノート作成時は差分確認のうえ必要に応じて修正してください。）