CHANGELOG
=========
すべての変更は Keep a Changelog の形式に従って記載しています。  
このファイルはリポジトリのコードベース（src/kabusys 以下）の内容から推測して作成した初回リリース向けの変更履歴です。

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-20
--------------------

Added
- パッケージ初期リリース (kabusys v0.1.0)
  - パッケージ公開情報:
    - src/kabusys/__init__.py にてバージョン 0.1.0 を設定。公開サブパッケージ: data, strategy, execution, monitoring。

- 設定・環境変数管理
  - src/kabusys/config.py
    - .env ファイルと環境変数の自動読み込み機能を実装（優先順位: OS 環境変数 > .env.local > .env）。
    - プロジェクトルートを .git または pyproject.toml から検出するロジックを導入（__file__ を基準に探索し CWD に依存しない）。
    - .env ファイルパーサーを実装: コメント行、export プレフィックス、クォート文字列（エスケープ対応）、インラインコメント処理などに対応。
    - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / システム環境（env, log_level）のプロパティを公開。環境値検証（有効な env 値・ログレベル）を実施。

- データ収集・保存 (J-Quants)
  - src/kabusys/data/jquants_client.py
    - J-Quants API クライアントを実装。主な機能:
      - 固定間隔スロットリングによるレート制限（120 req/min）。
      - リトライ（指数バックオフ、最大 3 回、408/429/5xx を対象）、429 の場合は Retry-After を考慮。
      - 401 応答時の自動トークンリフレッシュ（1 回のみ）とトークンキャッシュ（ページネーション間で共有）。
      - ページネーション対応の取得関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
      - DuckDB への冪等保存関数: save_daily_quotes, save_financial_statements, save_market_calendar（ON CONFLICT で更新）。
      - 取得値の型変換ユーティリティ (_to_float, _to_int) と fetched_at の UTC 記録。

- ニュース収集
  - src/kabusys/data/news_collector.py
    - RSS フィード収集の基盤実装。
    - 記事 ID を URL 正規化後の SHA-256（先頭 32 文字）で生成する方針（冪等性確保）。
    - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント除去、クエリソート）。
    - defusedxml を利用した XML パース（XML Bomb 等への対策）。
    - HTTP スキーム検証 / SSRF 対策、最大受信サイズ制限（MAX_RESPONSE_BYTES=10MB）、バルク INSERT のチャンク化等の堅牢化方針。

- リサーチ（ファクター計算・探索）
  - src/kabusys/research/factor_research.py
    - Momentum / Volatility / Value の定量ファクター計算を実装:
      - calc_momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200 日窓が揃わない場合は None）。
      - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio（ATR の NULL 伝播を正確に扱う）。
      - calc_value: per, roe（raw_financials の最新報告を target_date 以前から取得）。
    - DuckDB を用いた SQL + ウィンドウ関数で効率的に計算。

  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算 (calc_forward_returns)：複数ホライズン（デフォルト [1,5,21]）のリターンを一度に取得。
    - IC 計算 (calc_ic)：Spearman の ρ をランク変換して計算、サンプル不足時は None を返す。
    - 統計サマリー (factor_summary)、ランク変換ユーティリティ (rank) を実装。
    - pandas 等に依存せず標準ライブラリ + duckdb で完結。

  - src/kabusys/research/__init__.py で主要 API を再エクスポート。

- 戦略
  - src/kabusys/strategy/feature_engineering.py
    - build_features(conn, target_date): research モジュールから取得した生ファクターをマージ、ユニバースフィルタ（株価 >= 300 円、20 日平均売買代金 >= 5 億円）適用、Z スコア正規化（指定列）、±3 でクリップし features テーブルへ日付単位で置換（トランザクションで原子性を保証）。
    - ユニバースフィルタは過去の最新価格を参照して休場日等に対応。

  - src/kabusys/strategy/signal_generator.py
    - generate_signals(conn, target_date, threshold=0.60, weights=None):
      - features と ai_scores を統合し、momentum/value/volatility/liquidity/news のコンポーネントスコアを算出して重み付き合算で final_score を計算（デフォルト重みを定義）。
      - weights のバリデーションと合計 1 への正規化。無効な値は警告して無視。
      - Bear レジーム判定（ai_scores の regime_score 平均が負、十分なサンプル数が必要）。
      - BUY（threshold 超過）と SELL（ストップロス -8% / スコア低下）を生成。SELL を優先して BUY から除外。
      - signals テーブルへ日付単位の置換（トランザクションで原子性）。
    - 内部ユーティリティ: シグモイド変換、欠損値補完（中立 0.5）、スコア平均化など。

- データ統計ユーティリティ
  - src/kabusys/data/stats (参照のみ: zscore_normalize がリサーチ / strategy で利用されることを想定して re-export が行われている)

Changed
- 初期リリースのため該当なし（新規実装のみ）。

Fixed
- 初期リリースのため該当なし。

Security
- news_collector で defusedxml の使用、レスポンスサイズ制限、スキーマ検証、SSRF 対策等の措置を明示。
- jquants_client でトークンおよび HTTP エラー処理に注意した実装（自動リフレッシュ回数制限・再帰防止）。

Deprecated
- なし

Removed
- なし

Known issues / TODO
- 戦略のエグジット条件の一部が未実装（feature_engineering / signal_generator の docstring に記載）:
  - トレーリングストップ（直近最高値から -10%）および時間決済（保有 60 営業日超）を実装するには positions テーブルに peak_price / entry_date 等の追加フィールドが必要。
- src/kabusys/execution と monitoring パッケージはプレースホルダ（実装無しまたは最小実装の可能性）。
- 一部ロジックは外部環境（DuckDB スキーマ、テーブル定義、.env ファイルの存在、J-Quants API 設定など）に依存するため、実運用前に環境整備とテストが必要。
- news_collector の記事抽出・DB 保存フローは設計方針が明確だが、RSS の具体的なパース/挙動や SSRF 判定の閾値など運用時に調整が必要になる可能性あり。
- jquants_client の _request は urllib を用いた実装のため、高度な HTTP 機能（セッション管理、接続プール等）が必要な場合は requests 等への移行を検討。

内部ドキュメント・設計参照
- 各モジュール内 docstring に StrategyModel.md / DataPlatform.md 相当の設計意図や処理フローが記載されています。実装と整合する形でドキュメントを参照してください。

ライセンス・依存
- 標準ライブラリ中心の実装が意図されているが、duckdb, defusedxml 等の外部パッケージが前提です。実行環境にこれらをインストールしてください。

----------

この CHANGELOG はコード内容から推測して作成したため、実際のコミット履歴・変更差分とは異なる点があります。必要に応じて日付・項目の調整や追加情報（リリースノートリンク、比較 URL）をご指示ください。