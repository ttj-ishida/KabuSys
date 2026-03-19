# CHANGELOG

すべての注目すべき変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

## [0.1.0] - 2026-03-19

初回リリース。日本株自動売買システムの基盤となるモジュール群を追加しました。主要な機能、設計方針、セキュリティ対策、および DuckDB への永続化ロジックを含みます。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージ初期化（src/kabusys/__init__.py）。公開サブパッケージ: data, strategy, execution, monitoring。
  - バージョン情報を __version__ = "0.1.0" に設定。

- 設定管理 (src/kabusys/config.py)
  - .env ファイルと環境変数から自動的に設定を読み込む仕組みを実装。
  - プロジェクトルート探索（.git または pyproject.toml を基準）により CWD に依存しない自動読み込み。
  - 柔軟な .env パーサ（export プレフィックス対応、クォートとエスケープ対応、インラインコメント処理）。
  - 自動ロードの無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）。
  - 必須設定取得ヘルパー _require、Settings クラス（J-Quants トークン、kabu API、Slack、DBパス、環境判定、ログレベル検証等）を実装。
  - KABUSYS_ENV と LOG_LEVEL のバリデーション。

- データ取得・保存 (src/kabusys/data/)
  - J-Quants クライアント (src/kabusys/data/jquants_client.py)
    - API レート制御（120 req/min 固定間隔スロットリング）。
    - 再試行ロジック（指数バックオフ, 最大3回, 408/429/5xx を対象）。
    - 401 受信時の自動トークンリフレッシュ（1回のみ）とトークンキャッシュ共有。
    - ページネーション対応取得関数:
      - fetch_daily_quotes：日足データ取得（ページネーション対応）。
      - fetch_financial_statements：財務データ取得（ページネーション対応）。
      - fetch_market_calendar：JPX カレンダー取得。
    - DuckDB へ冪等に保存するユーティリティ:
      - save_daily_quotes：raw_prices テーブルへ ON CONFLICT DO UPDATE で保存。
      - save_financial_statements：raw_financials テーブルへ冪等保存。
      - save_market_calendar：market_calendar テーブルへ冪等保存。
    - 型変換ユーティリティ _to_float/_to_int と取得日時（fetched_at）を UTC で記録する方針（Look-ahead bias 防止）。

  - ニュース収集モジュール (src/kabusys/data/news_collector.py)
    - RSS フィード収集（DEFAULT_RSS_SOURCES に Yahoo Finance を含む）。
    - defusedxml を用いた安全な XML パース（XML Bomb 対策）。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ）。
      - リダイレクト先の事前検証（スキーム・プライベートアドレス判定）用ハンドラ。
      - ホスト/IP がプライベート/ループバック/リンクローカルの場合は拒否。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後の再検査（Gzip bomb 対策）。
    - URL 正規化（トラッキングパラメータ削除、クエリソート、フラグメント除去）と記事 ID の SHA-256 ベース生成（先頭32文字）。
    - テキスト前処理（URL 除去、空白正規化）。
    - raw_news へのチャンク化・トランザクション付き挿入（INSERT ... RETURNING を使用）および news_symbols への紐付け保存処理（重複除去、チャンク挿入）。
    - 銘柄コード抽出（4桁数字パターン、既知コードセットによるフィルタリング）。
    - 統合ジョブ run_news_collection によるソース毎の独立ハンドリングと結果集計。

  - DuckDB スキーマ定義 (src/kabusys/data/schema.py)
    - Raw 層テーブル DDL を追加（raw_prices, raw_financials, raw_news, raw_executions 等の定義を含む）。
    - 初期化用モジュールの基盤を実装（DataSchema に沿った 3 層構造の設計方針を記載）。

- リサーチ（特徴量・ファクター計算） (src/kabusys/research/)
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - calc_forward_returns：指定日から各ホライズン（デフォルト 1,5,21 営業日）先までの将来リターンを DuckDB の prices_daily テーブルから一括計算。
    - calc_ic：ファクター値と将来リターンのスピアマンランク相関 (Information Coefficient) を計算（欠測・非有限値排除、サンプル数閾値）。
    - rank：同順位は平均ランク扱い（浮動小数の丸めで ties 検出の安定化）。
    - factor_summary：count/mean/std/min/max/median を標準ライブラリのみで計算。
    - 設計方針として pandas 等外部ライブラリへ依存しない実装を採用。

  - ファクター計算 (src/kabusys/research/factor_research.py)
    - calc_momentum：mom_1m/mom_3m/mom_6m と ma200_dev（200日移動平均乖離率）を計算（ウィンドウ未満で None）。
    - calc_volatility：atr_20（20日 ATR）、atr_pct、avg_turnover、volume_ratio を計算（true_range の NULL 伝播を正確に扱う）。
    - calc_value：raw_financials から直近財務データを取り、PER（EPS が 0/NULL の場合は None）と ROE を計算。
    - スキャン範囲バッファやウィンドウサイズ定数を定義し、DuckDB のウィンドウ関数で効率的に集計。

- パッケージ公開（src/kabusys/research/__init__.py）
  - 研究用ユーティリティ群を __all__ で公開（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

### 変更 (Changed)
- N/A（初回リリースのため既存変更はありません）

### 修正 (Fixed)
- N/A（初回リリース）

### セキュリティ (Security)
- RSS 取得における SSRF 緩和（ホスト/IP の検査、リダイレクト前検証）。
- defusedxml による安全な XML パースで XML 関連攻撃を防止。
- ネットワーク入力のサイズ制限（最大 10MB）でメモリ DoS を軽減。
- URL 正規化によりトラッキングパラメータ除去・ID 重複検知の精度向上。

### 注意事項 (Notes)
- strategy/execution サブパッケージは現在モジュール初期化のみ（具体的な発注ロジックや注文処理は未実装）。実運用の発注・約定処理は今後実装予定。
- 多くの処理は DuckDB のテーブル（prices_daily, raw_financials, raw_prices, raw_news 等）を参照／更新するため、事前にスキーマ初期化と適切なデータ投入が必要です。
- .env 自動読み込みは便利ですが、テスト等で無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants API の認証には JQUANTS_REFRESH_TOKEN を設定する必要があります（Settings.jquants_refresh_token が未設定だと ValueError を送出）。
- 一部関数はデータ不足時に None を返す設計です（例：ウィンドウサイズ未満、EPS が 0/NULL 等）。上位での欠測値処理が必要です。

### 互換性 (Breaking Changes)
- なし（初回リリース）

---

将来的なリリースでは、strategy と execution の実装、モニタリング通知（Slack 連携のエンドポイント）、より詳細な DB マイグレーション/バージョン管理、単体テストの追加、パフォーマンス改善（並列取得等）を予定しています。必要であれば、これらのロードマップを別途 CHANGELOG または ROADMAP にまとめます。