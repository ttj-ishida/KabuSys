# Changelog

すべての変更は Keep a Changelog の慣例に従って記載しています。  
現在の安定バージョン: 0.1.0

## [Unreleased]

- なし

## [0.1.0] - 2026-03-20

### Added
- パッケージ初期リリース（KabuSys: 日本株自動売買システム）を追加。
- 基本パッケージ情報
  - src/kabusys/__init__.py にバージョン `0.1.0` と公開モジュール一覧を定義。
- 環境設定管理
  - src/kabusys/config.py
    - .env ファイルまたは OS 環境変数から設定を読み込む自動ロード機能を実装（プロジェクトルート検出: .git / pyproject.toml を探索）。
    - .env のパースに対応（コメント、`export KEY=val`、シングル/ダブルクォート、エスケープ、インラインコメントの扱いなど）。
    - 自動ロードを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` に対応。
    - 環境変数の保護（OS 環境変数を protected として .env.local の上書きから除外）。
    - 必須変数取得用の `_require`、`Settings` クラスを提供。J-Quants / kabu / Slack / DB パス等の設定プロパティを実装。
    - `KABUSYS_ENV` と `LOG_LEVEL` の許容値検証 (`development`, `paper_trading`, `live`、および標準ログレベル)。
    - パスは `Path.expanduser()` によってチルダ展開をサポート。
- データ取得・保存（J-Quants API）
  - src/kabusys/data/jquants_client.py
    - J-Quants API 用クライアントを実装（ページネーション処理、id_token キャッシュ、ID トークン自動リフレッシュ）。
    - レート制限管理（固定間隔スロットリングで 120 req/min を遵守）。
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を再試行対象、429 の Retry-After を尊重）。
    - JSON デコードエラーハンドリング、network エラーの再試行。
    - fetch_* 系関数: 日足（fetch_daily_quotes）、財務データ（fetch_financial_statements）、市場カレンダー（fetch_market_calendar）を実装。
    - DuckDB への保存用ユーティリティ: save_daily_quotes / save_financial_statements / save_market_calendar を実装。いずれも冪等性を担保するため ON CONFLICT（UPDATE）を使用。
    - レコード変換ユーティリティ `_to_float` / `_to_int` を実装（厳格な型変換ルール）。
    - 取得時刻は UTC で `fetched_at` に記録（Look-ahead バイアス対策）。
- ニュース収集
  - src/kabusys/data/news_collector.py
    - RSS フィードから記事を収集する基盤を実装（デフォルトソースに Yahoo Finance を設定）。
    - XML 解析に defusedxml を利用して XML Bomb 等の攻撃を軽減。
    - レスポンスサイズ上限（10 MB）を導入してメモリ DoS を防止。
    - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント削除、クエリソート）と記事 ID の生成（正規化後の SHA-256 の先頭 32 文字）で冪等性を確保。
    - URL 抽出・テキスト前処理（URL 除去・空白正規化）、バルク INSERT のチャンク処理を実装。
- リサーチ機能（研究用）
  - src/kabusys/research/factor_research.py
    - モメンタム（1M/3M/6M リターン、MA200 乖離）、ボラティリティ（20 日 ATR, atr_pct）、流動性（20 日平均売買代金、出来高比率）、バリュー（PER, ROE）を計算する関数を実装。
    - DuckDB の SQL ウィンドウ関数を活用した高速集計・欠損扱いを考慮。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）、IC（Spearman の ρ）計算、ファクター統計サマリーを実装。
    - ランク処理は同順位（ties）を平均ランクで扱う実装を提供。
  - research パッケージのエクスポートを提供（calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary / rank）。
- 特徴量エンジニアリング
  - src/kabusys/strategy/feature_engineering.py
    - 研究環境で計算した生ファクターを正規化・合成して features テーブルへ保存する `build_features` を実装。
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を実装。
    - Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップして外れ値影響を抑制。
    - 日付単位の置換（DELETE + INSERT）をトランザクションで行い冪等性と原子性を確保。
- シグナル生成
  - src/kabusys/strategy/signal_generator.py
    - features と ai_scores を統合し、component スコア（momentum/value/volatility/liquidity/news）に基づく最終スコア（final_score）を計算して BUY/SELL シグナルを生成する `generate_signals` を実装。
    - デフォルト重み・閾値（final_score >= 0.60 で BUY）を実装。ユーザ指定 weights を妥当性検査し正規化して使用。
    - AI レジームスコアの集計により Bear 相場を検知した場合、BUY を抑制するロジックを実装（サンプル不足時の誤判定回避も考慮）。
    - エグジット条件（ストップロス -8%、score の閾値未満）による SELL シグナル生成を実装。SELL 優先ルール（SELL 対象銘柄は BUY から除外）を適用。
    - signals テーブルへの日付単位置換（トランザクション＋バルク挿入）で原子性を担保。
- パッケージ API
  - src/kabusys/strategy/__init__.py で build_features / generate_signals を公開。
  - src/kabusys/research/__init__.py でリサーチユーティリティを公開。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- news_collector で defusedxml を使用し XML ベースの攻撃を緩和。
- news_collector の URL 正規化・スキーム/ホスト検査により SSRF 対策を考慮（実装中での注記あり）。
- J-Quants クライアントでトークン自動リフレッシュ・キャッシュを実装し、401 ハンドリングで不正な再帰を防止。

### Notes / Known limitations
- signal_generator のエグジット条件のうち、トレーリングストップや時間決済（保有 60 営業日超）などは未実装（positions テーブルに peak_price / entry_date が必要）。コード中に TODO として明記。
- news_collector の一部コメントにある「INSERT RETURNING で挿入数を正確に返す」等は設計方針として記載されているが、データベースバックエンド依存のため実運用での確認が必要。
- .env の自動ロードはプロジェクトルート検出に依存するため、配布後や特殊配置では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して手動ロードに切り替えることが可能。
- 外部依存をできるだけ抑えている（research モジュールは pandas 等に依存しない）が、実運用のスケーリングやパフォーマンスチューニングは今後の課題。

---

保持する慣例:
- 重大な後方互換性を壊す変更が発生した場合は Breaking changes を明示します（次回以降）。
- 追加・修正が行われたら Unreleased に追記し、リリース時にバージョンエントリを作成してください。