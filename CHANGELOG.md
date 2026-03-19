# CHANGELOG

すべての変更は Keep a Changelog の方針に従って記載しています。  
このファイルは、リポジトリ内のコード内容から推測して作成した初期リリースの変更履歴です。

フォーマット:
- 変更はセマンティックバージョニングに基づいて記載しています。
- 日付は本スナップショット公開日（2026-03-19）です。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-19

### Added
- パッケージ初期リリース: kabusys 0.1.0
  - サブパッケージ構成:
    - kabusys.config: 環境変数/設定管理
      - .env / .env.local の自動読み込み機能（プロジェクトルートは .git または pyproject.toml を探索）
      - 読み込み時の上書き制御（override）および OS 環境変数保護機構（protected）
      - .env パース実装（コメント/クォート/export 形式対応）
      - settings オブジェクトによる型安全な設定アクセス（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）
      - 環境値の検証 (KABUSYS_ENV, LOG_LEVEL) とヘルパープロパティ（is_live / is_paper / is_dev）
      - 自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD

    - kabusys.data.jquants_client: J-Quants API クライアント
      - API 呼び出しの共通処理: レートリミッタ（120 req/min 固定間隔スロットリング）
      - 再試行（指数バックオフ、最大 3 回）、HTTP 408/429/5xx のリトライ制御
      - 401 時の自動トークンリフレッシュ（1 回のみ）とモジュールレベルのトークンキャッシュ
      - ページネーション対応のデータ取得関数:
        - fetch_daily_quotes（株価日足）
        - fetch_financial_statements（財務データ）
        - fetch_market_calendar（JPX カレンダー）
      - DuckDB への冪等保存ユーティリティ:
        - save_daily_quotes（raw_prices へ ON CONFLICT DO UPDATE）
        - save_financial_statements（raw_financials へ ON CONFLICT DO UPDATE）
        - save_market_calendar（market_calendar へ ON CONFLICT DO UPDATE）
      - データ変換ユーティリティ: _to_float / _to_int
      - Look-ahead bias を防ぐための fetched_at の UTC 記録

    - kabusys.data.news_collector: RSS ニュース収集
      - RSS 取得 → 前処理 → raw_news への冪等保存のワークフロー（DataPlatform.md に準拠）
      - 記事 ID を URL 正規化後の SHA-256 ハッシュ（先頭 32 文字）で生成し冪等性を確保
      - URL 正規化: トラッキングパラメータ除去（utm_*, fbclid 等）、クエリソート、フラグメント削除、大文字小文字正規化
      - defusedxml を利用した XML パース（XML Bomb 等の対策）
      - HTTP レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）によるメモリ DoS 緩和
      - SSRF を防ぐためスキーム・ホスト等の検査を意識した実装方針
      - バルク INSERT のチャンク処理による SQL 長/パラメータ制限回避

    - kabusys.research: リサーチ用モジュール群
      - factor_research:
        - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率（ma200_dev）
        - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率
        - calc_value: latest raw_financials と prices_daily を組み合わせた PER / ROE 計算
        - 設計上 prices_daily / raw_financials のみ参照（本番 API 非依存）
      - feature_exploration:
        - calc_forward_returns: 指定ホライズンの将来リターン（デフォルト [1,5,21]）
        - calc_ic: スピアマンランク相関（IC）計算（欠損/サンプル不足時の保護）
        - factor_summary: count/mean/std/min/max/median の統計サマリ
        - rank: 同順位は平均ランクで扱うランク変換（丸めによる ties 対応）
      - 共通設計方針: DuckDB を用いた SQL ベースの高効率な集計、外部ライブラリに依存しない実装

    - kabusys.strategy: 戦略実行ロジック（取引シグナル生成）
      - feature_engineering.build_features:
        - research モジュールの生ファクターを統合して features テーブルへ保存（Z スコア正規化・±3 でクリップ）
        - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用
        - 日付単位で削除→挿入することで冪等性と原子性を担保（トランザクション）
      - signal_generator.generate_signals:
        - features と ai_scores を統合し、コンポーネント（momentum/value/volatility/liquidity/news）を計算
        - コンポーネントは欠損を中立 0.5 で補完、最終スコア final_score は重み付き合算
        - デフォルト重み: momentum=0.40, value=0.20, volatility=0.15, liquidity=0.15, news=0.10
        - BUY 閾値デフォルト 0.60
        - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数 >= 3 の場合）
        - エグジット判定（STOP LOSS -8% / スコア低下）
        - signals テーブルへ日付単位の置換（BUY / SELL を挿入）
        - weights の入力検証と自動再スケール（合計を 1.0 に補正）
        - SELL 優先ポリシー（SELL 対象は BUY から除外しランクを再付与）
      - 補助ユーティリティ: Z スコアをシグモイドに変換する _sigmoid、平均化ユーティリティ等

- 基本的なログ出力（logger）とエラーハンドリングを各モジュールに導入
  - トランザクション失敗時に ROLLBACK 試行とログ警告
  - データ欠損時のスキップログ（PK 欠損行等）

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- RSS パースに defusedxml を採用し XML 攻撃を軽減
- ニュース URL 正規化とトラッキングパラメータ除去、受信制限により SSRF / DoS リスクを考慮
- J-Quants クライアントでトークンリフレッシュ・リトライ制御を実装。HTTP エラーやネットワーク障害に対して安全に再試行する設計

### Notes / Design decisions
- DuckDB を一次ソースとして利用し、全ての集計・ファクター計算は DuckDB 上で完結する設計（外部 API に依存しない）
- ルックアヘッドバイアス回避のため、各処理は target_date 時点でシステムが知り得る情報のみを参照することを明記
- 各種保存処理は冪等性を重視（ON CONFLICT / 日付単位の DELETE→INSERT 等）
- 設定値や閾値は定数化しており、ドキュメント（コード内コメント）で設計根拠を記載

---

もし特定の変更点について詳細なリリースノート（例: 公開API仕様、DB スキーマ変更点、環境変数一覧、後方互換性の注意点など）を出力したい場合は、どの項目に焦点を当てるかを指示してください。