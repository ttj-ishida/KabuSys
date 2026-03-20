# Changelog

すべての注目すべき変更点を Keep a Changelog の形式に従って日本語で記載します。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-03-20
初回リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。以下はコードベースから推測される主要な追加・実装点および設計上の注意点です。

### Added
- 基本パッケージ
  - パッケージメタ情報（kabusys.__init__）を追加。__version__ = "0.1.0" を定義。
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ に含める。

- 環境設定
  - 環境変数・設定管理モジュールを実装（kabusys.config.Settings）。
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。
  - .env パーサの強化: export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメントの取り扱い、無効行スキップ。
  - OS 環境変数を保護する protected オプション、override フラグ、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード停止機能を提供。
  - 必須環境変数取得時の検査 (_require)、環境モード（development/paper_trading/live）とログレベル検証を実装。
  - デフォルトの API ベース URL や DB パス（DUCKDB_PATH / SQLITE_PATH）の既定値を設定。

- データ取得 / 保存系（kabusys.data）
  - J-Quants API クライアントを実装（jquants_client）。
    - 固定間隔のレートリミッタ（120 req/min）を実装。
    - 冪等なページネーション処理（pagination_key の追跡）。
    - リトライロジック（指数バックオフ、最大再試行 3 回、408/429/5xx を対象）。
    - 401 応答時はリフレッシュトークンで自動的に ID トークンを更新して再試行（1 回限定）。
    - Look-ahead バイアス対策のため fetched_at を UTC で記録。
    - DuckDB へ保存するユーティリティ（save_daily_quotes, save_financial_statements, save_market_calendar）を実装し、PK 欠損行のスキップや ON CONFLICT によるアップデート（冪等性）を考慮。
    - 型変換ユーティリティ (_to_float, _to_int) を実装し、不正値に対する安全な変換を行う。
  - ニュース収集モジュール（news_collector）を実装。
    - RSS フィード取得 → 正規化 → raw_news への冪等保存の処理フローを実装。
    - 記事ID に URL 正規化後の SHA-256 ハッシュ（先頭32文字）を使い冪等性を保証する設計。
    - defusedxml を使った XML パース（XML Bomb 等への防御）。
    - 受信サイズ上限（MAX_RESPONSE_BYTES）や SSRF 対策（HTTP/HTTPS のスキーム制限、ホスト検証）を組み込む設計意図。
    - トラッキングパラメータ除去、URL の正規化、バルク INSERT のチャンク処理を実装。

- 研究用モジュール（kabusys.research）
  - ファクター計算（factor_research）を実装:
    - モメンタム（1M/3M/6M リターン、200日移動平均乖離 ma200_dev）。
    - ボラティリティ / 流動性（20 日 ATR, atr_pct, avg_turnover, volume_ratio）。
    - バリュー（per, roe）— raw_financials から最新の財務データを取得。
    - DuckDB を用いた SQL ベースの実装、ウィンドウ関数による集計、欠損時の安全な None 処理。
  - 特徴量探索（feature_exploration）を実装:
    - 将来リターン計算（calc_forward_returns）: 指定ホライズンに対する forward returns を一括取得。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンランク相関を実装（rank ユーティリティ含む）。
    - ファクターの統計サマリ（factor_summary）: count/mean/std/min/max/median を計算。
  - research パッケージの公開 API を整理（calc_momentum/volatility/value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

- 戦略（kabusys.strategy）
  - 特徴量エンジニアリング（feature_engineering.build_features）を実装:
    - research モジュールから生ファクターを取得し、ユニバースフィルタ（最小株価・最小平均売買代金）を適用。
    - Z スコア正規化（zscore_normalize を利用）、±3 でクリップ。
    - features テーブルへの日付単位の置換（トランザクション + バルク挿入で冪等性・原子性を保証）。
    - ルックアヘッドバイアス回避（target_date 時点のみ参照）。
  - シグナル生成（signal_generator.generate_signals）を実装:
    - features と ai_scores を統合して momentum/value/volatility/liquidity/news のコンポーネントを計算。
    - コンポーネントの補完（None → 中立 0.5）やシグモイド変換を適用。
    - 重み（デフォルト値あり）を正規化して final_score を算出。カスタム weights の検証（未知キーや非数値を無視、合計が 1 でない場合は再スケール）を実施。
    - Bear レジーム判定を実装し、Bear の場合は BUY シグナルを抑制。
    - BUY（threshold デフォルト 0.60）と SELL（ストップロス -8% / スコア低下）の生成。保有ポジションの価格欠損時は SELL 判定をスキップする安全ロジック。
    - signals テーブルへの日付単位の置換（トランザクション + バルク挿入で原子性を保証）。
    - SELL が BUY を上書きする優先ポリシー（SELL 対象は BUY から除外しランク再付与）。

### Changed
- 設計注記（ドキュメント的な実装）
  - 多くのモジュールでルックアヘッドバイアス回避を明示（target_date 時点のみを参照）。
  - DuckDB を中心とした SQL/ウィンドウ関数ベースのデータ処理に統一。
  - 外部依存を最小化する方針（research の探索コードは pandas 等に依存しない）を採用。

### Fixed / Robustness
- env パーサと .env ロードの堅牢性向上（エスケープ／クォート／コメントの扱い、ファイル読み込み失敗時の警告）。
- J-Quants クライアントのネットワーク障害や HTTP エラーに対するリトライとバックオフを実装して安定性を向上。
- DuckDB への保存処理で PK 欠損行をスキップし、スキップ件数をログ警告で通知。
- トランザクション処理中の例外発生時に ROLLBACK を試行し、ROLLBACK 自体の失敗をログ出力。

### Security
- ニュース収集で defusedxml を利用して XML 攻撃を防御。
- URL 正規化とトラッキングパラメータ除去を実装し、記事冪等性の担保とプライバシー配慮を実施。
- ニュース取得で受信サイズ上限を設定し、メモリ DoS に対する防御を考慮。
- J-Quants クライアントでトークン管理を慎重に扱い、401 時の限定的な自動更新により無限再帰を回避。

### Notes / Known limitations
- execution/monitoring の実装はパッケージ公開はあるが、このリストに含まれるソースでは具体的な発注（kabu API）実装が未提供または空のまま（execution/__init__.py は空）。実運用では発注層の実装と本番 API 連携の追加が必要。
- 一部 SQL 文で ON CONFLICT を利用している（DuckDB の互換性に注意）。実行環境の DuckDB バージョンによっては文法差異があるため、マイグレーションやスキーマの整合性確認が必要。
- トレーリングストップや時間決済などの一部エグジット条件は未実装（positions テーブルに peak_price / entry_date 等が必要）。
- ニュース RSS のセキュリティ（SSRF 等）対策は設計上明記されているが、ホワイトリストや DNS 検証の具体実装は要確認。

---

この CHANGELOG は、提示されたソースコードからの推測に基づいて作成しています。実際のコミット履歴やリリースノートが存在する場合はそちらを優先してください。必要であれば各項目をより詳細なリリースノート形式（変更箇所ごとのファイルや関数名、想定された影響範囲、移行手順など）に拡張できます。