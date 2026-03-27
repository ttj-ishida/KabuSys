Keep a Changelog に準拠した CHANGELOG.md（日本語）を以下に作成しました。コード内容から推測して記載しています。

---
# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
このプロジェクトはセマンティックバージョニングに従います。詳細は <https://semver.org/> を参照してください。

## [Unreleased]
- 今後の変更や予定機能をここに記載します。

## [0.1.0] - 2026-03-27
初回リリース。日本株自動売買システム「KabuSys」の基盤機能を実装しました。

### 追加（Added）
- パッケージ初期化
  - kabusys パッケージのエントリポイントを追加（__version__ = 0.1.0、公開モジュール: data, strategy, execution, monitoring）。
- 環境設定管理（kabusys.config）
  - .env 自動読み込み機能を実装（プロジェクトルートの検出：.git または pyproject.toml を基準）。
  - .env/.env.local 読み込みの優先度制御（OS 環境変数を保護する protected 機構、override フラグ）。
  - .env 行パーサーの実装（export プレフィックス対応、クォート処理、インラインコメント処理）。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を実装。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 実行環境（development/paper_trading/live）/ログレベル等のプロパティを公開。
  - 環境変数未設定時に明示的にエラーを投げる _require() を実装。
- AI（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）の JSON モードで銘柄ごとのセンチメント（ai_score）を算出し ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウの算出（前日 15:00 JST ～ 当日 08:30 JST 相当の UTC 範囲）。
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄／呼び出し）、1 銘柄あたりの記事数・文字数制限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - リトライ（429・ネットワーク・タイムアウト・5xx）と指数バックオフ（最大試行回数・待機戦略）。
    - レスポンス検証（JSON 抽出、results 配列、code と score の型検証、既知コードのみ採用、スコアクリップ）。
    - 部分失敗時に既存スコアを残すための差し替え（DELETE→INSERT をコード単位で実行）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を算出し market_regime テーブルへ保存。
    - マクロニュースは news_nlp のウィンドウ関数 calc_news_window と整合（記事が無ければ LLM 呼び出しをスキップ）。
    - OpenAI 呼び出しは独立実装（モジュール間のプライベート関数共有を避ける）。
    - API エラーやパース失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
    - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。
- データ（kabusys.data）
  - カレンダー管理（calendar_management）
    - market_calendar テーブルに基づく営業日判定関数群を実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB にデータが無い場合は曜日ベースのフォールバック（週末を非営業日）を採用。
    - calendar_update_job による夜間バッチ（J-Quants API 経由で差分取得・バックフィル・保存）を実装。健全性チェックとバックフィル動作を備える。
  - ETL パイプライン（pipeline / etl）
    - ETLResult データクラスを公開（取得件数・保存件数・品質チェック結果・エラーメッセージ等を格納）。
    - 差分更新・バックフィル・品質チェックの設計方針を実装（_get_max_date 等のユーティリティ関数）。
    - jquants_client を経由した差分取得・idempotent 保存を想定した処理フローを想定。
- リサーチ（kabusys.research）
  - ファクター計算（factor_research）
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金、出来高比率）、バリュー（PER, ROE）を DuckDB 上の SQL/ウィンドウ関数で計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - 欠損やデータ不足時の挙動（例: 行数不足なら None）を明確化。
  - 特徴量探索（feature_exploration）
    - 将来リターン計算（calc_forward_returns: 任意ホライズンに対応）。
    - IC（Information Coefficient）計算（calc_ic: スピアマンのランク相関を実装）。
    - ランキングユーティリティ（rank: 同順位は平均ランクを与える）。
    - ファクター統計サマリー（factor_summary: count/mean/std/min/max/median）。
  - z-score 正規化ユーティリティを kabusys.data.stats 経由で再エクスポート（research パッケージの一部として利用可能）。
- データベース
  - DuckDB を主要な分析用ローカル DB として使用する設計。多くの処理で DuckDB の接続オブジェクトを引数に取る（テスト容易性）。
- ロギング／失敗対策
  - 各種処理で詳細なログ出力（INFO/WARNING/DEBUG）を実装。
  - API 呼び出しや DB 書き込み失敗時のフェイルセーフ（フォールバック値の使用、部分失敗を防ぐ差し替え戦略、トランザクション管理、ROLLBACK の試行）を組み込む。
- テストフレンドリネス
  - OpenAI 呼び出し関数をモジュール内で分離しており、unittest.mock.patch による差し替えが容易（_call_openai_api をモック可能）。

### 変更（Changed）
- 初版のため該当なし。

### 修正（Fixed）
- 初版のため該当なし。ただし設計上、API エラーや JSON パース失敗時に例外を投げずにフェイルセーフで続行する実装（news_nlp / regime_detector）を盛り込んでいます。

### 非推奨（Deprecated）
- なし

### 削除（Removed）
- なし

### セキュリティ（Security）
- 環境変数読み込みは .env ファイルから行われるが、OS 環境変数は protected として優先される仕様を採用し、意図しない上書きを防止。
- OpenAI API キーは引数で注入可能（テスト時の差し替え容易化）で、未設定時は ValueError を発生させ明示的に扱う。

### 既知の注意点（Notes / Known issues）
- 外部 API（J-Quants / OpenAI）や DuckDB のバージョン差異に依存する部分があるため、本番運用前にエンドツーエンドの確認を推奨します。
- OpenAI のレスポンスは JSON mode を使用する想定だが、稀に前後の余計なテキストが混在するケースに備え JSON の抽出処理を実装しています。完全な互換性保証は API 側の挙動に依存します。
- strategy, execution, monitoring パッケージは __all__ で公開されているが、このリリースに含まれる具体的な発注ロジック・監視実装の有無はコードベースに依存します（必要に応じて追加実装を行ってください）。

---

（必要なら、各モジュールごとの詳細な変更履歴や使い方サンプルを別途用意できます。どの情報を優先して追加しますか？）