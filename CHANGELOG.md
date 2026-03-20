Keep a Changelog
=================

すべての変更はセマンティックバージョニングに従います。  
このファイルは Keep a Changelog の形式に準拠しています。

[Unreleased]
------------

(なし)

[0.1.0] - 2026-03-20
-------------------

初期リリース。日本株自動売買システム "KabuSys" のコア機能を実装しました。以下はコードベースから推測してまとめた主要な追加点・設計上の注記です。

Added
- パッケージ基盤
  - パッケージ名: kabusys, バージョン 0.1.0
  - エクスポート: data, strategy, execution, monitoring（execution と monitoring の詳細実装は別ファイル想定）

- 設定管理 (kabusys.config)
  - .env ファイル・環境変数自動読み込み機能を実装
    - プロジェクトルート検出: .git または pyproject.toml を基準に探索（CWD 非依存）
    - 読み込み優先順位: OS 環境 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化
    - .env パーサー: export 構文、クォート内エスケープ、インラインコメントに対応
    - 上書き制御 (override) と保護キーセット (protected) により OS 環境の上書きを防止
  - Settings クラスで主要設定を型安全に取得
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など必須チェック
    - データベースパス (DUCKDB_PATH, SQLITE_PATH) の Path 返却
    - 環境（KABUSYS_ENV）／ログレベル（LOG_LEVEL）の検証メソッドと is_live / is_paper / is_dev のヘルパー

- データ収集 / 保存 (kabusys.data.jquants_client)
  - J-Quants API クライアント
    - 固定間隔スロットリングによるレート制御（120 req/min）
    - リトライ（指数バックオフ、最大 3 回）、408/429/5xx を再試行対象に設定
    - 401 受信時の自動トークンリフレッシュ（1 回のみ）とトークンキャッシュ
    - ページネーション対応（pagination_key）
    - データ取得関数: fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
    - DuckDB への保存関数（冪等）
      - save_daily_quotes -> raw_prices（ON CONFLICT DO UPDATE）
      - save_financial_statements -> raw_financials（ON CONFLICT DO UPDATE）
      - save_market_calendar -> market_calendar（ON CONFLICT DO UPDATE）
    - 入力パースユーティリティ: _to_float / _to_int（データ不整合に寛容な変換）
    - fetched_at を UTC ISO8601 で付与し、Look-ahead バイアス対応

- ニュース収集 (kabusys.data.news_collector)
  - RSS 取得・前処理・保存パイプライン
    - デフォルト RSS ソース (Yahoo 等) を定義
    - URL 正規化: トラッキングパラメータ除去（utm_*, fbclid 等）、クエリソート、フラグメント除去
    - レスポンスサイズ制限 (MAX_RESPONSE_BYTES = 10MB)
    - defusedxml を使った XML パースで XML-Bomb 等の対策
    - 記事 ID は正規化 URL の SHA-256（先頭 32 文字）で生成して冪等性を確保
    - SSRF 対策の意識、HTTP/HTTPS スキームの検証等の方針が記載（実装の一部）
    - バルク INSERT のチャンク化とトランザクションまとめ込み（パフォーマンス、原子性）

- 研究用モジュール (kabusys.research)
  - ファクター計算 (factor_research)
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200 日移動平均）
    - calc_volatility: atr_20 / atr_pct / avg_turnover / volume_ratio（20 日ベース）
    - calc_value: per / roe（raw_financials から最新財務を参照）
    - SQL と窓関数を組み合わせて DuckDB 上で効率的に計算
  - 特徴量探索 (feature_exploration)
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターン計算（LEAD による）
    - calc_ic: スピアマンのランク相関（Information Coefficient）計算
    - factor_summary: 各ファクターの count/mean/std/min/max/median を算出
    - rank: 同順位の平均ランク処理（round を用いた ties 対応）
  - zscore_normalize を外部から利用可能にエクスポート（kabusys.data.stats 実装依存）

- 戦略モジュール (kabusys.strategy)
  - 特徴量エンジニアリング (feature_engineering.build_features)
    - research で算出した生ファクターをマージ、ユニバースフィルタ (price, avg_turnover)、Zスコア正規化、±3 クリップ
    - DuckDB の features テーブルに対して日付単位で置換（DELETE + バルク INSERT）し原子性を保証（トランザクション）
  - シグナル生成 (signal_generator.generate_signals)
    - features と ai_scores を統合して各コンポーネントスコア（momentum/value/volatility/liquidity/news）を算出
    - コンポーネントはシグモイド変換・平均化で正規化し、重み付き合算で final_score を算出（デフォルト重みを定義）
    - Bear レジーム判定（AI の regime_score 平均が負かつサンプル数閾値以上）
    - BUY: threshold (デフォルト 0.60) を超える銘柄をランク付け（Bear 時は BUY 抑制）
    - SELL: 保有ポジションに対するエグジット判定（ストップロス -8%、スコア低下）
    - signals テーブルに対して日付単位で置換（トランザクション＋バルク挿入）
    - 重みの入力検証（未知キーや負値・NaNを無視、合計が 1 でない場合は再スケール）

- ロギング / エラーハンドリング
  - 各処理に logger を挿入し注意喚起（warnings）やデバッグ情報を出力
  - DB トランザクションで例外発生時は ROLLBACK を試行し失敗時は警告

Security / Safety
- データ取得・パースにセキュリティ対策を組み込み
  - defusedxml の利用（XML パースの安全化）
  - RSS URL 正規化とトラッキングパラメータ除去（プライバシー配慮）
  - レスポンスサイズ制限（メモリ DoS 対策）
  - SSRF 対策方針の明記

Performance / Reliability
- レートリミッタ、リトライ、指数バックオフによる外部 API 呼び出しの堅牢化
- DuckDB へのバルク挿入、トランザクションまとめ込み、ON CONFLICT による冪等性
- ページネーション中のトークンキャッシュで認証効率化

Known limitations / TODO
- signal_generator の SELL 判定中に記載のトレーリングストップと時間決済は未実装（positions テーブルに peak_price / entry_date が必要）
- 一部の安全対策は方針・チェックの明記に留まり、追加実装が必要な箇所がある（例: ニュース記事の SSRF 完全防止のためのソケット/IP 検査等）
- news_collector の記事→銘柄紐付け（news_symbols）など上流結合の詳細は別実装を想定
- _to_int の仕様により "1.9" などの値は None を返す（意図的な切り捨て回避）
- 外部依存: duckdb, defusedxml を使用（軽量な研究/運用向け設計）

Removed
- (なし)

Changed
- (初回リリースのため該当なし)

Fixed
- (初回リリースのため該当なし)

Notes
- 本 CHANGELOG は提供されたソースコードから設計意図と実装を推測して作成したものであり、実際の変更履歴（コミット単位）とは一致しない場合があります。詳細なコミット履歴やリリースノートが必要な場合は、バージョン管理履歴（git log）を参照してください。