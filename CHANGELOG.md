# CHANGELOG

すべての変更は Keep a Changelog の方針に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/

なお、本 CHANGELOG は与えられたコードベースから推測して作成しています（実装・設計に関する注記を含む）。

## [Unreleased]

## [0.1.0] - 2026-03-19

### 追加 (Added)
- 基本パッケージ構成を追加
  - パッケージ名: kabusys、バージョン 0.1.0（src/kabusys/__init__.py）。
  - モジュール: data, research, strategy, execution, monitoring（execution/monitoring はプレースホルダを含む）。

- 環境設定管理 (`kabusys.config`)
  - .env ファイルおよび環境変数から設定を自動読み込み（プロジェクトルート判定: .git または pyproject.toml を探索）。
  - 読み込み順: OS 環境変数 > .env.local > .env（.env.local は .env をオーバーライド）。
  - 自動ロードの無効化: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で可能。
  - .env パーサの実装: export KEY=val、クォート文字列（エスケープ対応）、インラインコメントの扱いなどをサポート。
  - 設定取得ラッパー Settings を提供（J-Quants トークン・kabu API パスワード・Slack トークン/チャンネル・DB パス・環境種別・ログレベル等）。
  - env/log_level 値の妥当性チェック（allowed 値集合）。

- データ取得・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
  - レート制限対応: 固定間隔スロットリング（120 req/min, min interval = 60 / 120 秒）。
  - 再試行ロジック: 指数バックオフ、最大リトライ 3 回（408/429/5xx 等を対象）。429 の場合には Retry-After を尊重。
  - 401 Unauthorized 受信時は ID トークンを自動リフレッシュして 1 回だけ再試行（無限再帰を防止）。
  - ページネーション対応の fetch_... 関数:
    - fetch_daily_quotes（株価日足）
    - fetch_financial_statements（財務データ）
    - fetch_market_calendar（取引カレンダー）
  - DuckDB への保存関数（冪等）:
    - save_daily_quotes -> raw_prices（ON CONFLICT DO UPDATE）
    - save_financial_statements -> raw_financials（ON CONFLICT DO UPDATE）
    - save_market_calendar -> market_calendar（ON CONFLICT DO UPDATE）
  - 保存時に fetched_at を UTC ISO8601 で記録。
  - 型変換ユーティリティ: _to_float / _to_int（不正な値は None とする堅牢な実装）。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードから記事を収集・前処理・raw_news へ冪等保存する機能。
  - デフォルト RSS ソースに Yahoo Finance（business）を含む。
  - セキュリティ対策:
    - defusedxml を用いて XML 攻撃を防止。
    - 受信サイズ上限（10 MB）でメモリ DoS を軽減。
    - URL 正規化でトラッキングパラメータ（utm_*, fbclid 等）を除去。
    - 記事 ID は正規化後 URL の SHA-256 ハッシュ先頭を用いて冪等性を担保。
    - SSRF 対策を意識した URL スキーム制限等の方針（コード上の注記）。
  - バルク挿入のチャンク化（パフォーマンス／SQL 長対策）。

- 研究用ツール (kabusys.research)
  - factor_research: モメンタム・ボラティリティ・バリューの計算関数を実装。
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（21/63/126/200 日等の定数）。
    - calc_volatility: 20 日 ATR（atr_20 / atr_pct）、20 日平均売買代金、出来高比率。
      - true_range は high/low/prev_close のいずれも NULL の場合に NULL とする等、欠損伝播を慎重に扱う。
    - calc_value: raw_financials から target_date 以前の最新財務を結合して PER / ROE を算出。
  - feature_exploration:
    - calc_forward_returns: デフォルト horizons = [1,5,21]、LEAD を使った将来リターン計算、horizons の妥当性チェック (<=252)。
    - calc_ic: スピアマンランク相関（IC）計算、データ不足時は None を返す（有効サンプル >= 3 が必要）。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリ。
    - rank: 同順位は平均ランクを割り当てる実装（丸め誤差対策として round(..., 12) を使用）。

- 特徴量作成 (kabusys.strategy.feature_engineering)
  - research モジュールで算出した raw factor を正規化 / フィルタ / 合成して features テーブルへ保存する処理を実装。
  - ユニバースフィルタ:
    - 最低株価 _MIN_PRICE = 300 円
    - 20 日平均売買代金 _MIN_TURNOVER = 5e8 円（5 億円）
  - 正規化: kabusys.data.stats の zscore_normalize を用い、対象カラムに対して Z スコア化を行う（対象カラム: mom_1m, mom_3m, atr_pct, volume_ratio, ma200_dev）。
  - 外れ値クリップ: Z スコアを ±3（_ZSCORE_CLIP）でクリップ。
  - DB 書き込みは日付単位で DELETE→INSERT の置換（トランザクションで原子性を保証）。

- シグナル生成 (kabusys.strategy.signal_generator)
  - features と ai_scores を統合して final_score を算出し、BUY/SELL シグナルを作成して signals テーブルへ保存。
  - スコア構成要素: momentum / value / volatility / liquidity / news（デフォルト重みを定義）。
    - デフォルト重み: momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10
  - BUY 閾値デフォルト: 0.60
  - 重みの扱い:
    - ユーザ与件は既知キーのみ受け付け、非数値・負値・NaN/Inf は無視。
    - 合計が 1 でない場合は再スケール。
  - コンポーネントスコアの計算:
    - momentum: 複数シグナル(20/60 日モメンタム、ma200_dev) を sigmoid → 平均
    - value: PER に基づく変換（PER=20 => 0.5、PER→0 => 1、PER→∞ => 0）
    - volatility: atr_pct の Z スコアを反転して sigmoid
    - liquidity: volume_ratio を sigmoid
    - news: ai_score を sigmoid（未登録は中立扱い）
    - 欠損コンポーネントは中立値 0.5 で補完して扱う（欠損銘柄の不当な降格を防止）
  - Bear レジーム検出:
    - ai_scores の regime_score 平均が負かつサンプル数 >= 3 の場合 Bear と判定し BUY シグナルを抑制。
  - エグジット（SELL）ロジック:
    - ストップロス: (close / avg_price - 1) < -8% (_STOP_LOSS_RATE)
    - スコア低下: final_score < threshold
    - NOTE: トレーリングストップや時間決済は未実装（positions テーブルに peak_price / entry_date が必要）。
  - signals テーブルへの書き込みも日付単位で置換（トランザクションで原子性）。

### 変更 (Changed)
- （初回リリースのため該当なし）  

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 既知の制限 (Known issues / Limitations)
- 一部のエグジット条件は未実装:
  - トレーリングストップ（peak_price に基づく -10% など）
  - 時間決済（保有 60 営業日超過など）
  - これらは positions テーブルに peak_price / entry_date が必要であり、将来実装予定。
- 一部の外部依存を避ける設計:
  - research/feature_exploration では pandas 等に依存せず標準ライブラリのみで実装しているため、大規模データ処理の最適化やメモリ効率は今後改善の余地あり。
- News Collector の URL 正規化・SSRF 対応は設計方針として考慮済みだが、運用上の追加検証が必要（例: 外部ネットワークポリシーやプロキシ環境）。

### セキュリティ (Security)
- RSS パーサに defusedxml を利用し XML 攻撃を軽減。
- J-Quants クライアントはトークン管理・自動リフレッシュの実装により 401 に対処。ただし実運用ではトークン管理・シークレット保護に注意。

---

参考: 実装上の主要定数・ポリシー
- ユニバースフィルタ: 最低株価 = 300 円、最低平均売買代金 = 5 億円
- Z スコアクリップ: ±3
- J-Quants API レート制限: 120 req/min、再試行最大 3 回
- シグナル閾値（デフォルト）: BUY >= 0.60、ストップロス = -8%
- research calc_forward_returns デフォルト horizons = [1,5,21]、horizons は正の整数かつ <= 252

（以上）