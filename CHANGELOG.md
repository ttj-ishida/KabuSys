# Changelog

すべての notable な変更点を記録します。  
このファイルは「Keep a Changelog」準拠で記載しています。

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Security: セキュリティ関連の注意

## [0.1.0] - 2026-03-20

初回公開リリース。日本株自動売買システムのコア機能群を実装しています。

### Added
- パッケージ基盤
  - kabusys パッケージを追加。バージョンは 0.1.0。
  - top-level のエクスポート: data, strategy, execution, monitoring（__all__）。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイルと環境変数を読み込む自動ロード実装。
    - プロジェクトルートの検出は .git または pyproject.toml を基準に行う（CWD に依存しない実装）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロードを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサ実装（コメント、exportプレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理などに対応）。
  - 環境変数取得ヘルパーと Settings クラスを提供（J-Quants / kabu API / Slack / DB パス / システム設定など）。
  - 設定値検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）。

- データ取得・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアント実装。
    - 固定間隔スロットリングによるレート制御（120 req/min）。
    - リトライ（指数バックオフ、最大3回、408/429/5xx に対応）。
    - 401 時の自動トークンリフレッシュ（1 回のみ）とモジュールレベルのトークンキャッシュ。
    - ページネーション対応で fetch_* 系関数を実装:
      - fetch_daily_quotes（株価日足）
      - fetch_financial_statements（財務）
      - fetch_market_calendar（マーケットカレンダー）
    - レスポンスの JSON デコード失敗時の明確なエラー報告。
  - DuckDB への冪等保存機能を実装:
    - save_daily_quotes → raw_prices（ON CONFLICT DO UPDATE）
    - save_financial_statements → raw_financials（ON CONFLICT DO UPDATE）
    - save_market_calendar → market_calendar（ON CONFLICT DO UPDATE）
    - 各変換ユーティリティ (_to_float, _to_int) を実装し不正データの安全な取り込みをサポート。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードから記事を収集・正規化し raw_news に保存する基盤を実装。
  - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント除去、ソートされたクエリ）を実装。
  - セキュリティ対策:
    - defusedxml を使用して XML Bomb 等を防止。
    - 受信サイズ上限（MAX_RESPONSE_BYTES）を設置（メモリ DoS 対策）。
    - 非 HTTP/HTTPS スキームの拒否や SSRF を意識した実装方針を採用。
  - バルク INSERT のチャンク処理で DB のオーバーヘッドを低減。

- リサーチ / ファクター計算 (kabusys.research)
  - ファクター計算モジュール（prices_daily / raw_financials を参照）:
    - calc_momentum（1M/3M/6M リターン、MA200 乖離）
    - calc_volatility（ATR20、相対 ATR、平均売買代金、出来高比率）
    - calc_value（PER、ROE を価格と結合して計算）
  - 特徴量探索ユーティリティ:
    - calc_forward_returns（任意ホライズンの将来リターン計算。デフォルト [1,5,21]）
    - calc_ic（スピアマン ρ による IC 計算。サンプル数が 3 未満なら None を返す）
    - factor_summary（count/mean/std/min/max/median の集計）
    - rank（同順位は平均ランクで処理。丸め誤差対策あり）

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - 研究環境で計算した raw ファクターをマージ → ユニバースフィルタ → 正規化（zscore）→ ±3 でクリップ → features テーブルに UPSERT（冪等）する処理を実装。
  - ユニバースフィルタ条件:
    - 株価 >= 300 円
    - 20 日平均売買代金 >= 5 億円
  - Z スコア正規化は kabusys.data.stats の zscore_normalize を使用。

- シグナル生成 (kabusys.strategy.signal_generator)
  - features と ai_scores を統合して final_score を計算し、BUY/SELL シグナルを生成して signals テーブルに日付単位の置換で保存する処理を実装。
  - 初期重みと閾値を実装（デフォルト weights と threshold=0.60）。
  - コンポーネントスコア:
    - momentum（momentum_20, momentum_60, ma200_dev）
    - value（PER を基に逆数的に変換）
    - volatility（atr_pct を反転して低ボラほど高スコア）
    - liquidity（volume_ratio）
    - news（AI スコアのシグモイド変換、未登録時は中立補完）
  - AI レジームスコアに基づく Bear 判定（サンプル数閾値あり）。Bear 相場時は BUY シグナルを抑制。
  - SELL 条件（実装済）:
    - ストップロス: 終値 / avg_price - 1 < -8%
    - スコア低下: final_score が threshold 未満
  - SELL 優先ポリシー（SELL 対象は BUY リストから除外）。

### Security
- 外部インプットの厳格な扱い:
  - news_collector は defusedxml を使用し XML の脆弱性を低減。
  - news_collector は受信データサイズ上限を設けることでメモリ DoS を軽減。
  - jquants_client は認証トークン管理と自動リフレッシュ、レート制御、リトライを実装し外部 API 対応の堅牢化を図る。

### Notes / Known limitations
- 一部 exit 条件は未実装（コメント記載）:
  - トレーリングストップ（直近最高値からの -10%）および時間決済（保有 60 営業日超）には positions テーブルに peak_price / entry_date が必要であり、現状未実装。
- news_collector による銘柄紐付け（news_symbols）や記事→銘柄マッチングの詳細実装は今後の拡張項目。
- 外部依存:
  - duckdb、defusedxml 等が必要（README や packaging に依存関係を明記することを推奨）。
- Python の型注釈に union 型（|）を使用しているため、Python 3.10 以上を想定している可能性が高い。

### Breaking Changes
- 初回リリースのため該当なし。

### Contributors
- (コードベースから自動抽出できる情報がないため、必要であれば実際の貢献者名を追記してください)

---

今後のリリースで想定する改善点（例）
- positions テーブルの拡張（peak_price / entry_date）に伴うトレーリングストップ・時間決済の実装
- news_collector の多ソース対応・記事→銘柄マッチング精度向上（NLP/辞書ベースの強化）
- モニタリング・実行層（execution / monitoring）の実装と API 統合
- テストカバレッジの拡充と CI による自動検証

必要であれば、この CHANGELOG を英語版に翻訳したり、リリース日や貢献者情報を更新したりできます。どのように調整しますか？