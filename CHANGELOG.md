Keep a Changelog
=================

すべての重要な変更をこのファイルに記載します。  
このプロジェクトは "Keep a Changelog" の方針に従ってバージョニングしています。

フォーマット:
- 変更はセクション (Added, Changed, Fixed, ...) に分類
- 各リリースは日付付きで記載

Unreleased
----------

- （現在未リリースの変更はありません）

0.1.0 - 2026-04-01
------------------

Added
- パッケージ初期リリースを追加
  - パッケージバージョン: 0.1.0（src/kabusys/__init__.py）
  - パブリック API のエクスポート: data, strategy, execution, monitoring

- 環境設定管理機能を追加（src/kabusys/config.py）
  - .env および .env.local 自動読み込み（プロジェクトルートを .git または pyproject.toml から検出）
  - 読み込み優先順位: OS 環境変数 > .env.local > .env
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト等向け）
  - .env パーサを実装（コメント、export プレフィックス、シングル／ダブルクオート、バックスラッシュエスケープに対応）
  - 環境変数保護（既存 OS 環境変数を protected として上書き抑止）
  - Settings クラスを提供し、各種設定をプロパティ経由で取得
    - J-Quants / kabuステーション / Slack / DB パス / 監視閾値 / システム設定（KABUSYS_ENV, LOG_LEVEL）のバリデーション
    - デフォルト値と Path 型変換を提供

- ニュース NLP（AI）機能を追加（src/kabusys/ai/news_nlp.py）
  - calc_news_window: ニュース集計ウィンドウ（JST 基準 → UTC naive）計算ユーティリティ
  - score_news: raw_news + news_symbols から銘柄ごとにニュースを集約して OpenAI（gpt-4o-mini）でセンチメント解析し ai_scores テーブルへ書き込み
    - バッチ処理（最大 20 銘柄／API コール）
    - 1銘柄あたりの最大記事数・文字数トリム（トークン肥大対策）
    - JSON Mode の応答を堅牢にパース（前後ノイズの復元処理含む）
    - レスポンス検証（results 配列、code/score の型チェック、未知コードの無視、スコアの ±1.0 クリップ）
    - レートリミット・ネットワークエラー・5xx に対する指数バックオフリトライ
    - 部分失敗を考慮した冪等的 DB 書き込み（対象コードのみ DELETE → INSERT）
    - テスト容易性のため _call_openai_api をモック可能に設計
    - 処理中のログ出力で進捗・失敗を記録

- 市場レジーム判定機能を追加（src/kabusys/ai/regime_detector.py）
  - score_regime: ETF 1321 の 200日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して market_regime テーブルへ書き込み
    - ma200_ratio 計算（ルックアヘッド防止のため target_date 未満のデータのみ使用）
    - raw_news からマクロキーワードでフィルタしてタイトルを収集
    - OpenAI（gpt-4o-mini）へ JSON 出力を要求し macro_sentiment を取得
    - API 失敗時は macro_sentiment = 0.0 にフォールバック（フェイルセーフ）
    - 冪等的 DB トランザクション（BEGIN / DELETE / INSERT / COMMIT）での書き込み
    - リトライロジック、HTTP 5xx とそれ以外の扱いの分離、ログ出力

- リサーチ（ファクター／特徴量探索）機能を追加（src/kabusys/research/）
  - factor_research.py
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離を計算（データ不足時の None ハンドリング）
    - calc_volatility: 20日 ATR、相対 ATR、平均売買代金、出来高比率を計算（NULL 伝播に注意）
    - calc_value: raw_financials から最新財務データを取得し PER/ROE を計算
    - DuckDB SQL を利用し、外部 API へアクセスしない設計
  - feature_exploration.py
    - calc_forward_returns: 任意ホライズンの将来リターンを一括取得（ホライズン検証あり）
    - calc_ic: スピアマン（ランク相関）による IC 計算（不足データ時は None）
    - rank: 同順位は平均ランクで処理（丸めによる ties 回避）
    - factor_summary: count/mean/std/min/max/median の集計

- データプラットフォーム機能を追加（src/kabusys/data/）
  - calendar_management.py
    - JPX カレンダー管理ユーティリティ（market_calendar テーブル）
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供
    - calendar_update_job: J-Quants からの差分取得 → market_calendar へ冪等保存（バックフィル、健全性チェック含む）
    - DB 未取得時の曜日ベースフォールバック、最大探索日数で安全策を実装
  - pipeline.py / etl.py
    - ETLResult データクラスを実装（取得件数・保存件数・品質問題・エラー概要などを保持）
    - ETL の設計方針（差分更新、バックフィル、品質チェックの収集式設計、id_token 注入可能）を反映
    - data.etl モジュールで ETLResult を再エクスポート

- ロギングとエラーハンドリング
  - 各モジュールは詳細なログ出力を行い、API エラーや DB エラー時に例外伝播またはフェイルセーフなフォールバックを実施
  - ファイル読み込み失敗時に warnings.warn（.env 読み込み）

Changed
- 安全性と品質重視の設計を採用
  - ルックアヘッドバイアス対策: datetime.today()/date.today() をスコアリング内部で参照しない（target_date を明示）
  - DB 書き込みは冪等的に行う（DELETE → INSERT、ON CONFLICT を想定）
  - DuckDB の古いバージョン互換性を考慮（executemany に空リストを渡さない guard）
  - OpenAI 呼び出しはモジュール間でプライベート関数を共有せず、テストで差し替え可能に実装

Fixed
- API 応答パースの堅牢化
  - JSON Mode で前後に余計なテキストが混入する場合の復元ロジックを追加
  - レスポンスのスキーマ不整合や数値変換失敗時は該当レコードをスキップし続行する実装

Notes / Design decisions
- OpenAI への依存はあるが、API エラー時は中立スコア（0.0）でフェイルセーフに継続する実装により上位処理の安定性を優先
- 多くの処理で明示的に target_date を受け取る設計（テスト可能性と再現性の担保）
- .env パーサはシェルライクな書式を広くサポート（export, quote, escape, inline comment）
- 一部モジュールはテストしやすいよう内部呼び出しを差し替え可能（ユニットテスト向けのフックを用意）

Security
- 本リリースでのセキュリティ修正は特になし（OpenAI API キーや各種シークレットは Settings 経由で管理する想定。実運用ではシークレット管理に注意）

Unknown / TODO
- 一部ファイル（pipeline.py の末尾など）に未完・途切れが見受けられる箇所があるため、次リリースでの補完・リファクタを予定
- strategy / execution / monitoring パッケージの実装詳細（本リリースでの公開はインターフェース中心）

以上

-----