CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。  
リリースは後方互換性の観点でセマンティックバージョニングに従います。

[Unreleased]: https://example.com/changelog/unreleased
[0.1.0]: https://example.com/changelog/0.1.0

## [0.1.0] - 2026-03-20

初回リリース。日本株自動売買システム「KabuSys」の基本機能を実装しました。主にデータ取得・保存、ファクター計算、特徴量エンジニアリング、シグナル生成、設定管理およびニュース収集に関するコアモジュールを含みます。

### Added
- パッケージ基盤
  - パッケージエントリポイント: kabusys.__version__ = "0.1.0" と __all__ の公開（data, strategy, execution, monitoring）。
- 環境設定管理 (kabusys.config)
  - .env ファイル／環境変数からの設定読み込みロジックを実装。
  - プロジェクトルート判定: .git または pyproject.toml を基準に自動検索（CWD に依存しない）。
  - .env/.env.local の自動ロード（優先順位: OS 環境 > .env.local > .env）。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサー: export プレフィックス・クォート・エスケープ・インラインコメント対応（複雑な値の取り扱いをサポート）。
  - Settings クラス: J-Quants / kabuステーション / Slack / DB パス / 実行環境（development/paper_trading/live）/ログレベル等のプロパティを提供。必須値未設定時に明示的なエラーを投げる _require()。

- データ取得・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
  - レート制限対応: 固定間隔スロットリング（120 req/min）による RateLimiter を導入。
  - 再試行ロジック: 指数バックオフ（最大3回）、ステータスコード 408/429/5xx に対するリトライ、429 の Retry-After 優先処理。
  - 401 Unauthorized 対応: ID トークン自動リフレッシュを行い 1 回リトライ。
  - ページネーション対応で fetch_* 系関数（fetch_daily_quotes、fetch_financial_statements、fetch_market_calendar）を実装。
  - DuckDB への保存関数を実装（save_daily_quotes、save_financial_statements、save_market_calendar）。いずれも冪等性を保証する ON CONFLICT / DO UPDATE を採用。
  - データ整形ユーティリティ (_to_float / _to_int)、UTC の fetched_at 記録（Look-ahead バイアス管理に寄与）。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィード収集器を実装（デフォルトソースに Yahoo ファイナンスのビジネス RSS を設定）。
  - セキュリティ対策: defusedxml を使用、受信サイズ上限（10 MB）、HTTP/HTTPS スキーム制限など。
  - URL 正規化: トラッキングパラメータ（utm_* など）削除、スキーム/ホスト小文字化、フラグメント削除、クエリソート。
  - 記事 ID は正規化 URL の SHA-256 ハッシュ（先頭 32 文字）で生成し、冪等保存を保証。
  - DB へのバルク挿入はチャンク化して実行（パフォーマンスと SQL パラメータ上限対策）。news_symbols 等との紐付け設計を想定。

- 研究用ファクター計算・探索 (kabusys.research)
  - ファクター計算 (kabusys.research.factor_research)
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日移動平均乖離）を計算。データ不足時は None を返す。スキャン範囲はウィンドウバッファで休日を吸収。
    - calc_volatility: 20日 ATR、atr_pct、20日平均売買代金、出来高比率を計算。true_range の NULL 伝播を適切に制御。
    - calc_value: raw_financials から最新財務情報を取得し PER / ROE を計算。EPS 欠損やゼロへの対処あり。
  - 特徴量探索 (kabusys.research.feature_exploration)
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）に対する将来リターンを計算。horizons の入力検証あり。
    - calc_ic: ファクターと将来リターンの Spearman ランク相関（IC）を計算。有効サンプル数が 3 未満なら None を返す。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。
    - rank: 同順位（タイ）を平均ランクに処理するランク計算ユーティリティ。
  - 研究モジュールは外部ライブラリ（pandas 等）に依存しない実装方針。

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - build_features を実装:
    - research モジュールから生ファクターを取得（momentum / volatility / value）。
    - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を適用。
    - 数値ファクターは zscore_normalize（kabusys.data.stats を利用）で正規化し ±3 でクリップ。
    - features テーブルへ日付単位で置換（DELETE + INSERT）しトランザクションで原子性を保証。
    - 休場日等に対応するため target_date 以前の最新株価を参照する価格取得ロジックを実装。

- シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals を実装:
    - features と ai_scores を統合して、momentum/value/volatility/liquidity/news のコンポーネントスコアを計算。
    - 各コンポーネントはシグモイド変換や PER に基づく変換等で [0,1] に変換。
    - 欠損コンポーネントは中立値 0.5 で補完。
    - デフォルト重みを持ち、ユーザ渡しの weights は検証・スケーリングしてマージ（合計 1 に正規化）。
    - Bear レジーム判定: ai_scores の regime_score 平均が負の場合に BUY シグナルを抑制（サンプル数閾値あり）。
    - BUY シグナル生成は閾値（デフォルト 0.60）以上で生成、SELL は保有ポジションに対するストップロス（-8%）およびスコア低下で判定。
    - SELL を優先し、SELL 対象は BUY リストから除外、signals テーブルへ日付単位で置換して書き込み。
    - weights の不正値は警告してスキップする堅牢化。

- パッケージ公開
  - kabusys.strategy.__init__ で build_features / generate_signals を公開。
  - kabusys.research.__init__ で主要な研究関数群を公開。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Deprecated
- （初版のため該当なし）

### Removed
- （初版のため該当なし）

### Security
- ニュース収集で defusedxml を採用し XML 攻撃を軽減。
- RSS URL/受信のバリデーション、受信サイズ上限を設けてメモリ DoS を軽減。
- J-Quants クライアントのトークン管理・自動リフレッシュは認証エラー時の安全な再取得を考慮。

### Known limitations / TODO
- signal_generator のエグジット（_generate_sell_signals）では以下の条件は未実装（コード内に注記あり）:
  - トレーリングストップ（peak_price の管理）
  - 時間決済（保有日数上限）
  これらは positions テーブルに追加情報（peak_price / entry_date 等）が必要。
- news_collector は URL と記事テキストの銘柄マッチング（news_symbols との紐付け）を想定しているが、外部完全自動紐付けロジックは今後の実装対象。
- データ処理の一部（zscore_normalize など）は kabusys.data.stats に依存（本リリースでは参照実装を前提とする）。

---

参照:
- 本 CHANGELOG はリポジトリ内のドキュメント注釈およびソースコードの docstring から推測して作成しています。具体的な使用法・ API の詳細は該当モジュールの docstring を参照してください。