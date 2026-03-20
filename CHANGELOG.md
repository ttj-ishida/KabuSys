# Changelog

すべての重大な変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

現在のバージョン: 0.1.0

## [0.1.0] - 2026-03-20

初回公開リリース。本リポジトリは日本株の自動売買システム（KabuSys）のコアライブラリ群を提供します。主にデータ取得・前処理・ファクター計算・シグナル生成・研究用ユーティリティを含み、DuckDB をデータ層として利用する設計になっています。

### 追加 (Added)
- パッケージ基盤
  - パッケージ名: kabusys、バージョン定義 __version__ = "0.1.0" を追加。
  - パブリック API エクスポート: build_features, generate_signals 等を __all__ に追加。

- 環境設定/ロード機能 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む自動ロード実装（プロジェクトルートを .git / pyproject.toml で検出）。
  - .env / .env.local の読み込み順序（OS 環境変数 > .env.local > .env）と上書き制御を実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードの無効化が可能。
  - export KEY=val 形式やコメント、シングル/ダブルクォート、エスケープに対応した .env ラインパーサを実装。
  - Settings クラスを実装し、J-Quants トークン・kabu API パスワード・Slack トークン・データベースパス・環境（development/paper_trading/live）・ログレベルなどの取得・検証を提供。

- データ取得クライアント (src/kabusys/data/jquants_client.py)
  - J-Quants API クライアントを実装（ページネーション・再試行・トークンリフレッシュ対応）。
  - レート制限対策: 固定間隔スロットリングを実装（120 req/min の保護）。
  - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx の再試行、429 の Retry-After 利用）。
  - 401 応答時はリフレッシュトークンから id_token を再取得して1回リトライする仕組み。
  - データ取得関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar を実装。
  - DuckDB への保存関数（冪等）: save_daily_quotes, save_financial_statements, save_market_calendar（ON CONFLICT で更新）。
  - データ取り込み時に fetched_at を UTC で記録し、Look-ahead バイアス追跡を可能に。

- ニュース収集 (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を収集して raw_news に保存する基礎機能を追加。
  - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント除去、パラメータソート）実装。
  - セキュリティ対策: defusedxml を利用して XML 攻撃を防御、HTTP(s) 以外のスキーム拒否、受信サイズ上限導入（10MB）など。
  - 記事 ID を正規化 URL の SHA-256 ハッシュで生成して冪等性を確保。
  - DB へのバルク保存でチャンク処理を導入。

- 研究／ファクター計算 (src/kabusys/research/*.py, src/kabusys/research/factor_research.py)
  - ファクター計算モジュール（calc_momentum, calc_volatility, calc_value）を実装。
    - Momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日MA乖離率）を計算。
    - Volatility: 20日 ATR、atr_pct、20日平均売買代金、出来高比率を計算。
    - Value: per（株価/EPS）、roe を raw_financials と prices_daily から計算。
  - 研究用ユーティリティ: calc_forward_returns（複数ホライズンの将来リターン算出）、calc_ic（Spearman ランク相関 / IC）、factor_summary（統計サマリ）、rank（同順位は平均ランク）を実装。
  - DuckDB の SQL を主軸に純粋 Python（外部依存を極力排除）で実装。

- 特徴量エンジニアリング (src/kabusys/strategy/feature_engineering.py)
  - research モジュールの生ファクターを読み取り、ユニバースフィルタ（最低株価/流動性）適用、Z スコア正規化、±3でクリップ、features テーブルへ日付単位で UPSERT（削除→挿入）する build_features を実装。
  - ユニバース判定閾値: 最低株価 300 円、20 日平均売買代金 5 億円を採用。
  - ルックアヘッドバイアスを防ぐため target_date 時点のデータのみを使用。

- シグナル生成 (src/kabusys/strategy/signal_generator.py)
  - features と ai_scores を統合して final_score を計算、BUY/SELL シグナルを生成する generate_signals を実装。
  - スコア構成要素: momentum/value/volatility/liquidity/news（デフォルト重みを実装、外部から重みを与え合計正規化）。
  - シグモイド変換・中立補完（欠損時は 0.5）・Z スコア クリップ済み前提でのスコア計算を実装。
  - Bear レジーム検知（AI の regime_score 平均が負であれば BUY を抑制）を実装（サンプル数下限あり）。
  - エグジット条件（SELL）: ストップロス（-8%）およびスコア低下（閾値未満）。SELL は BUY より優先。
  - signals テーブルへ日付単位で置換（トランザクションにより原子性を保証）。

- データ統計ユーティリティ (src/kabusys/data/*.py)
  - 型変換補助: _to_float / _to_int。入力の堅牢性向上（空値・不正文字列の安全処理）。

### 変更 (Changed)
- 初版のため該当なし。

### 修正 (Fixed)
- 初版のため該当なし。

### セキュリティ (Security)
- news_collector で defusedxml を利用、RSS パースで XML 攻撃を軽減。
- ニュース収集時に受信サイズ制限を導入しメモリ DoS を軽減。
- news_collector で SSRF 対策（HTTP/HTTPS スキームのみ許可）やトラッキングパラメータ除去を実施。
- J-Quants クライアントでトークンリフレッシュと安全な再試行を実装。

### 既知の制限・未実装点 (Notes / TODO)
- signal_generator 内の一部エグジット条件（トレーリングストップ、時間決済）は未実装（positions テーブルに peak_price / entry_date が必要）。
- news_collector の詳細な URL バリデーション（IP 判定等）や外部フィードの多様化は今後の拡張対象。
- 一部の SQL は DuckDB を前提としているため、他の DB では互換性に制限がある可能性あり。
- 外部依存を最小化する設計のため、解析処理に pandas 等を使用していない（大規模データでの性能チューニングは今後検討）。

---

今後のリリースでは以下を想定しています:
- execution 層（kabu ステーションや実際の発注ロジック）の追加実装。
- テストカバレッジ拡充と CI 用のセットアップ（自動化）。
- News—シンボル紐付け自動化（NLP によるエンティティ抽出）などの強化。

（この CHANGELOG はコード内の docstring と実装から推測して作成しています。）