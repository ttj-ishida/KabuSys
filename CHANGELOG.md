# Changelog

すべての重要な変更は Keep a Changelog に準拠して記載します。  
比較的初期のリリース（v0.1.0）として、システム全体の基礎機能を実装しています。  
（内容はソースコードから推測してまとめたものです）

全体の設計方針（抜粋）
- DuckDB をデータ基盤として利用（atomic な日付単位置換、トランザクションで整合性を確保）
- ルックアヘッドバイアス回避（target_date 時点のデータのみ参照、fetched_at を UTC で記録）
- 冪等性重視（DB への保存は ON CONFLICT / DO UPDATE 等で上書き）
- 本番発注層（execution）への直接依存を排し、戦略と実行を分離
- セキュリティ／堅牢性対策（XML パースに defusedxml、RSS の受信サイズ制限、SSRF 回避方針等）

Unreleased
- （現時点なし）

## [0.1.0] - 2026-03-20

Added
- パッケージ基盤
  - パッケージメタ情報と公開 API を定義（kabusys.__init__、strategy/execution/monitoring の公開）
- 環境設定管理（kabusys.config）
  - .env 自動読み込み（プロジェクトルートは .git または pyproject.toml を探索）
  - .env と .env.local の読み込み順序（OS 環境変数 > .env.local > .env）。.env.local は override（上書き）される
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能
  - 高度な .env パーサ実装（export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱い）
  - 未設定時に例外を投げる必須設定取得ヘルパ（Settings クラス）
  - 各種設定プロパティを実装（J-Quants トークン、kabu API、Slack、DB パス、環境 / ログレベル検証、is_live/is_paper/is_dev 等）
- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアント実装（ページネーション対応）
  - レートリミット制御（固定間隔スロットリング、120 req/min を満たす実装）
  - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx をリトライ対象）
  - 401 受信時にリフレッシュトークンで ID トークンを自動更新して再試行（1 回だけ）
  - fetch_* / save_* 系関数を提供:
    - fetch_daily_quotes / save_daily_quotes（raw_prices へ保存、PK 欠損スキップ、ON CONFLICT DO UPDATE）
    - fetch_financial_statements / save_financial_statements（raw_financials へ保存、PK 欠損スキップ、ON CONFLICT DO UPDATE）
    - fetch_market_calendar / save_market_calendar（market_calendar へ保存、取引日/半日/SQ の扱い）
  - 数値変換ユーティリティ（_to_float / _to_int）で不正値を安全に None に変換
  - API 呼び出しは fetched_at を UTC ISO8601 で記録（Look-ahead のトレース可能性）
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得基盤（デフォルトに Yahoo Finance ビジネスカテゴリを定義）
  - セキュリティ対策: defusedxml による XML パース（XML Bomb 等の防御）、受信サイズ上限（10MB）、HTTP/HTTPS のみ許可などの方針
  - URL 正規化ユーティリティ（トラッキングパラメータ削除、スキーム/ホストの小文字化、フラグメント除去、クエリソート）
  - 記事 ID の生成仕様（URL 正規化後の SHA-256 ハッシュ（先頭32文字）を用いる方針を明記）
  - バルク INSERT のチャンク化（_INSERT_CHUNK_SIZE=1000）で DB オーバーヘッドを軽減
  - raw_news テーブルへの冪等保存（ON CONFLICT DO NOTHING を想定）
  - 設計上、記事と銘柄の紐付け（news_symbols）を行う方針を明記
- 研究（research）モジュール
  - ファクター計算（kabusys.research.factor_research）
    - calc_momentum（1M/3M/6M リターン、200 日 MA 乖離率）
    - calc_volatility（20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率）
    - calc_value（直近財務データを用いて PER / ROE を算出）
    - 各関数は prices_daily / raw_financials のみ参照し、データ不足時の None 処理を実装
  - 特徴量探索（kabusys.research.feature_exploration）
    - calc_forward_returns（指定 horizon リストに対する将来リターン計算、データがない場合は None）
    - calc_ic（スピアマンのランク相関による IC 計算。サンプル不足（<3）時は None）
    - factor_summary（count/mean/std/min/max/median を算出）
    - rank（同順位の平均ランクを割当てる実装。比較前に round(v, 12) で丸める）
  - research パッケージの __all__ に主要関数を集約
- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features 実装:
    - research モジュールの生ファクターを取得（momentum/volatility/value）
    - ユニバースフィルタ（最小株価 300 円、20 日平均売買代金 >= 5億円）
    - 指定の数値カラムを Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）
    - 正規化値を ±3 でクリップ（外れ値抑制）
    - features テーブルへ日付単位での置換（DELETE → bulk INSERT、トランザクションで原子性保証）
    - ロギング（処理数の INFO 出力）
- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals 実装:
    - features, ai_scores, positions テーブルを参照してシグナル生成
    - コンポーネントスコア: momentum / value / volatility / liquidity / news を算出
      - シグモイド変換や逆数変換（PER）等のロジックを実装
    - デフォルト重みを定義（momentum 0.4, value 0.2, volatility 0.15, liquidity 0.15, news 0.1）
      - ユーザ指定の weights は検証（未知キーや非数値は無視）、合計が 1.0 になるよう再スケール
    - Bear レジーム判定: ai_scores の regime_score の平均が負かつサンプル数 >= 3 で Bear と判定し BUY を抑制
    - BUY シグナル閾値デフォルト 0.60
    - SELL シグナル（エグジット判定）:
      - ストップロス（終値 / avg_price - 1 < -8%）を最優先
      - final_score が threshold 未満で SELL
      - positions の価格欠損時は SELL 判定をスキップして誤クローズを防止
    - BUY/SELL を signals テーブルへ日付単位で置換（DELETE → bulk INSERT、トランザクションで原子性保証）
    - SELL 優先ポリシー（SELL 対象は BUY から除外してランクを再付与）
    - 生成件数の INFO ログ出力
- トランザクション管理とロールバックの扱い
  - features / signals などの置換処理で BEGIN/COMMIT を使用し、例外時は ROLLBACK を試行。ROLLBACK 失敗時は警告ログを出す実装

Security
- XML パースに defusedxml を採用（news_collector）
- RSS 受信サイズ上限（10MB）でメモリ DoS を軽減
- URL 正規化でトラッキングパラメータ除去、HTTP/HTTPS 以外のスキーム拒否方針（設計メモ）
- API 呼び出しに対して認証トークンの自動更新とリトライを実装（401 → トークンリフレッシュ）

Changed
- 初回リリースのため該当なし

Fixed
- 初回リリースのため該当なし

Removed
- 初回リリースのため該当なし

Notes / Known limitations / TODO
- signal_generator のエグジット条件に記載されている「トレーリングストップ（直近最高値から -10%）」や「時間決済（保有 60 営業日超過）」は positions テーブルに peak_price / entry_date 等が必要であり、現バージョンでは未実装（コメントで TODO として明記）
- news_collector の記事 → 銘柄紐付け処理（news_symbols への挿入など）は設計方針に記載されているが、ソース中の実装（ファイル末尾の続き）は省略・補完が必要な可能性あり
- execution パッケージは存在するが、発注ロジック（kabu API 経由の実際の約定処理等）は本リリースでは実装依存（空パッケージまたは実装外）
- 一部ユーティリティ（kabusys.data.stats.zscore_normalize）の実装は別ファイルに依存（本差分ではファイル未掲示）

開発者向けメモ
- テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動 .env 読み込みを抑制してください
- DuckDB スキーマ（raw_prices, raw_financials, prices_daily, features, ai_scores, positions, signals, market_calendar, raw_news 等）は本コードが前提としているため、ローカルで動作させる際はスキーマ定義を用意してください

--- 

今後のリリース候補
- execution 層（実際の注文送出・約定待ち処理）の実装
- news_collector の完全実装（XML パース→DB 保存→銘柄紐付け→AI スコア連携）
- ポジション管理の拡張（peak_price / entry_date の保存、トレーリングストップ実装）
- テレメトリ・メトリクス収集、より詳細なログ/監視機能

（以上）