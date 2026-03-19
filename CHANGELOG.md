Changelog
=========
すべての重要な変更履歴はここに記録します。  
このファイルは "Keep a Changelog" の形式に準拠しています。  

1.0.0 より前の開発 | 0.1.0 (2026-03-19)
-------------------------------------
Added
- 初回公開リリース (0.1.0)：
  - 全体
    - パッケージ初期構成を追加（kabusys パッケージ、__version__ = 0.1.0、主要サブモジュールを __all__ で公開）。
  - 環境設定 (src/kabusys/config.py)
    - .env / .env.local の自動読み込み機構を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
    - .env パーサを実装。export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント処理、無効行スキップに対応。
    - 自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - Settings クラスを実装。J-Quants / kabu / Slack / DB / ログ等の設定プロパティを提供し、必須環境変数未設定時に明確な例外を投げる。
    - KABUSYS_ENV / LOG_LEVEL の値検証（許容値のチェック）を実装。
  - データ取得・保存 (src/kabusys/data/)
    - J-Quants API クライアント (jquants_client.py)
      - 固定間隔のレートリミッタ実装（120 req/min、モノトニック時間ベース）。
      - HTTP リクエストユーティリティに指数バックオフ＋リトライを実装（最大 3 回、408/429/5xx を対象）。
      - 401 発生時の自動トークンリフレッシュを 1 回だけ試行するロジックを実装。
      - ページネーション対応の fetch_*/save_* 関数を実装（daily_quotes、financial_statements、market_calendar）。
      - DuckDB への保存は冪等（ON CONFLICT DO UPDATE）で実行。fetched_at を UTC で記録。
      - 型変換ユーティリティ _to_float / _to_int を用意し堅牢にパース。
    - ニュース収集モジュール (news_collector.py)
      - RSS フィードからの記事収集の基礎実装（デフォルトソースに Yahoo Finance を設定）。
      - URL 正規化（トラッキングパラメータ除去・ソート・フラグメント削除・スキーム/ホスト小文字化）を実装。
      - defusedxml を用いた XML パース（XML Bomb 等の防御）。
      - 受信サイズ上限（10 MB）や SSRF 緩和の設計方針を採用。
      - 記事 ID を正規化 URL の SHA-256（先頭 32 文字）で生成し冪等性を確保。
  - 研究用モジュール (src/kabusys/research/)
    - ファクター計算 (factor_research.py)
      - Momentum / Volatility / Value 系の定量ファクター計算を実装（prices_daily / raw_financials を参照）。
      - 移動平均、ATR、出来高比率、PER などを計算。過不足データ時は None を返す取り扱いを採用。
    - 特徴量探索 (feature_exploration.py)
      - 将来リターン計算（calc_forward_returns、任意ホライズンの一括取得）を実装。
      - IC（Spearman の ρ）計算の calc_ic、ランク付け関数 rank、統計サマリー factor_summary を実装。
      - pandas 等外部依存なしで標準ライブラリ + DuckDB SQL による実装。
  - 戦略モジュール (src/kabusys/strategy/)
    - 特徴量エンジニアリング (feature_engineering.py)
      - research モジュールの生ファクターを取り込み、ユニバースフィルタ（最低株価 / 平均売買代金）を適用。
      - 数値ファクターを Z スコア正規化（zscore_normalize を利用）し ±3 でクリップ。
      - features テーブルへ日付単位で置換（削除→挿入のトランザクション処理、冪等）。
    - シグナル生成 (signal_generator.py)
      - features と ai_scores を統合し、momentum/value/volatility/liquidity/news のコンポーネントスコアを算出。
      - シグモイド変換や欠損値を中立値(0.5)で補完する方針を採用。
      - デフォルト重みと閾値を提供。外部から渡された weights は検証・補完・正規化（合計=1へリスケーリング）。
      - Bear レジーム判定（ai_scores の regime_score 平均が負の場合）で BUY シグナル抑制。
      - SELL（エグジット）判定：ストップロス（-8%）およびスコア低下による判定を実装。保有ポジション情報の参照と価格欠損時のスキップ処理を実装。
      - signals テーブルへ日付単位置換（トランザクション＋バルク挿入）。
  - その他
    - DuckDB を前提とした SQL 実装（WINDOW 関数、多数の集約/ウィンドウ式利用）。
    - ロギング（各処理での info/debug/warning の適切な出力）。
    - 重要設計・注意点を docstring に明記（ルックアヘッドバイアス対策、冪等性、テスト容易性）。

Security
- ニュースパーシングに defusedxml を採用することで XML 関連の攻撃リスクを低減。
- RSS URL 正規化・トラッキングパラメータ除去・受信バイト上限・HTTP スキームの制約等で SSRF / メモリ DoS のリスクを軽減する設計方針を採用。

Known limitations / Notes
- signal_generator の SELL 判定におけるトレーリングストップ・時間決済は未実装（コメントで将来実装の意図を記載）。positions テーブルに peak_price / entry_date が必要。
- news_collector の詳細な URL ホワイトリスト / IP ブラックリストチェックは設計方針として言及されているが、実行時の追加制約は実装状況に依存する。
- DuckDB のテーブル定義（スキーマ）や外部環境（.env.example 等）はこのリリースには含まれないため、運用にはスキーマと環境変数の準備が必要。
- jquants_client のリトライ対象ステータスやリトライ回数、レート制限はコード内定数で管理。実運用でのパラメータ調整が可能。

Unreleased / Future
- trailing stop / time-based exit のエグジット条件実装予定（positions テーブル拡張が前提）。
- news_collector の記事と銘柄の紐付け（news_symbols への格納）ロジック強化、記事のテキスト追加前処理の強化（言語処理）を検討。
- テストカバレッジ拡充（.env 解析・API クライアントのモック・DuckDB 用ユニットテスト等）。

ライセンス・作者情報
- 各モジュールの docstring に設計方針・想定動作を記載。README / .env.example / DB スキーマは別途整備してください。

（注）上記はソースコードから推測可能な機能・設計方針に基づく CHANGELOG です。実際のリリース手順や配布物に含めるべきドキュメント（例: スキーマ定義・環境変数サンプル・運用手順）は別途追加してください。