# Changelog

すべての注目すべき変更を記録します。本ファイルは「Keep a Changelog」仕様に準拠します。  

状態: 初期公開リリースをコードベースから推測して作成しています。

※ バージョン番号はパッケージの __version__ (src/kabusys/__init__.py) に合わせています。

## [Unreleased]
- 今後の実装予定（ソース内の docstring や TODO から推測）
  - execution 層（発注ロジック）の具体的実装
  - monitoring パッケージの追加（__all__ に含まれるが実体が未提供）
  - ポジション管理に必要な positions テーブルの拡張（peak_price / entry_date 等）と、それに基づくトレーリングストップ・時間決済の実装
  - 単体テスト・統合テストの追加
  - パフォーマンス改善や並列取得の検討（J-Quants 取得処理など）

---

## [0.1.0] - 2026-03-20
初回公開（コードベースの内容から推測）

### Added
- 基本パッケージ構成を追加
  - パッケージルート: kabusys（src/kabusys）
  - エントリ: __version__ = "0.1.0"
  - __all__ に data, strategy, execution, monitoring を公開

- 環境変数・設定管理 (src/kabusys/config.py)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込み
  - 自動ロードを環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能
  - .env ファイルのパースを独自実装（コメント・export 句・シングル/ダブルクォート・エスケープ処理に対応）
  - Settings クラスを提供し、J-Quants / kabuAPI / Slack / DB パス / 実行環境 (development/paper_trading/live) / ログレベルの取得・バリデーションを実装

- データ取得・保存 (src/kabusys/data)
  - J-Quants クライアント (jquants_client.py)
    - 固定間隔スロットリングによるレート制限制御（120 req/min）
    - リトライ（指数バックオフ、最大3回）および 401 受信時のトークン自動リフレッシュ
    - ページネーション対応・ページ間でのトークンキャッシュ共有
    - 取得データを DuckDB に冪等に保存する save_daily_quotes / save_financial_statements / save_market_calendar
    - 型変換ユーティリティ (_to_float / _to_int) を実装し不正値を安全に扱う
  - ニュース収集モジュール (news_collector.py)
    - RSS 取得 → 正規化 → raw_news への冪等保存フロー
    - URL正規化（トラッキングパラメータ削除・ソート・フラグメント除去）による記事ID生成
    - defusedxml を用いた XML 攻撃対策、受信サイズ制限、SSRF/不正スキーム対策、バルク挿入チャンク制御
    - デフォルト RSS ソース（Yahoo Finance）定義

- リサーチ（研究用）機能 (src/kabusys/research)
  - ファクター計算 (factor_research.py)
    - Momentum（mom_1m, mom_3m, mom_6m, ma200_dev）
    - Volatility（atr_20, atr_pct, avg_turnover, volume_ratio）
    - Value（per, roe） — raw_financials と prices_daily の組合せで計算
    - 各関数は DuckDB の prices_daily / raw_financials に依存し、(date, code) キーの dict リストを返す
  - 特徴量探索・統計 (feature_exploration.py)
    - 将来リターン計算（calc_forward_returns: 複数ホライズン対応、1/5/21 デフォルト）
    - IC（Information Coefficient）計算（calc_ic: Spearman のρ）
    - 基本統計サマリー（factor_summary）
    - ランキングユーティリティ（rank）
    - 外部依存（pandas 等）なしで実装

- ストラテジー（strategy） (src/kabusys/strategy)
  - 特徴量エンジニアリング (feature_engineering.py)
    - research モジュールから生ファクターを取得し、ユニバースフィルタ（最低株価/最低売買代金）を適用
    - Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）および ±3 でクリップ
    - features テーブルへ日付単位で置換（トランザクション + バルク挿入で原子性保証）
  - シグナル生成 (signal_generator.py)
    - features と ai_scores を統合して最終スコア（final_score）を計算
    - momentum/value/volatility/liquidity/news の重み付け合算（デフォルト重みを実装）
    - 重みの入力検証と合計が1になるよう正規化（不正値はログでスキップ）
    - Bear レジーム検出（ai_scores の regime_score 平均が負の場合）による BUY 抑制
    - BUY シグナル閾値（デフォルト 0.60）、STOP LOSS（-8%）を実装
    - 保有ポジションに対する SELL 判定（stop_loss, score_drop）
    - signals テーブルへ日付単位で置換（トランザクション + バルク挿入で原子性保証）

- データ統計ユーティリティ公開 (src/kabusys/research/__init__.py)
  - calc_momentum / calc_volatility / calc_value / zscore_normalize / calc_forward_returns / calc_ic / factor_summary / rank を __all__ で再公開

### Changed
- （初回リリース相当）ドキュメント重視の実装
  - 各モジュールに詳細な docstring を付与（設計方針・処理フロー・注記・未実装項目の明示）
  - DuckDB を前提とした SQL クエリ設計（ウィンドウ関数を多用）でパフォーマンスと正確性を両立

### Fixed / Hardening
- .env パーサーの堅牢化
  - export キーワード対応、クォート内のバックスラッシュエスケープ、コメント判定ルール等を実装し意図しないパースを防止
  - プロジェクトルート探索を __file__ ベースで行い CWD に依存しない自動読み込みを実現
- J-Quants API クライアントの堅牢化
  - レート制御、リトライ、429 の Retry-After 尊重、401 での一度のみのトークンリフレッシュとキャッシュ更新
  - ページネーション対応とページネーショントークンの二重取得防止
- DuckDB 保存の冪等性を確保（ON CONFLICT / DO UPDATE を使用）
- ニュース収集時のセキュリティ対策（defusedxml, レスポンスサイズ制限, URL 正規化）を導入

### Known limitations / Not implemented
- positions テーブルの拡張に依存するトレーリングストップ・時間決済が未実装（feature doc に明示）
- execution 層（実際の発注／kabu API 連携）の具象実装は含まれない（execution パッケージの中身が未実装）
- monitoring は __all__ に入っているがパッケージ実体が未提供
- 一部の算出は十分な過去データがない場合 None を返す仕様（欠損やサンプル不足はログで扱う）
- research モジュールは外部ライブラリを使わず純 Python/SQL で実装しているため、大量データに対するメモリ/速度チューニングが今後の課題

### Security
- ニュース収集: XML パースに defusedxml を使用して XML-Bomb 等の攻撃を緩和
- ニュース URL の正規化・トラッキングパラメータ除去により偽装や追跡パラメータの影響を低減
- J-Quants クライアント: ネットワークエラーや不正レスポンスに対する堅牢なエラーハンドリング（JSON デコード失敗時の例外化など）

---

開発・運用チーム向けメモ（コードから推測）
- .env.example を用意して必須環境変数（JQUANTS_REFRESH_TOKEN / SLACK_BOT_TOKEN 等）を文書化することを推奨（Settings._require に基づく）
- DuckDB スキーマ（prices_daily / raw_prices / raw_financials / features / ai_scores / positions / signals / market_calendar / raw_news 等）を事前に整備する必要あり
- 実行環境（development / paper_trading / live）に応じたログレベル・API エンドポイント設定を行うこと

以上。必要であれば、この CHANGELOG を英語に翻訳したり、各項目をファイル/行単位でさらに詳細化して差分参照用に整形します。どの形式がよいか指示してください。