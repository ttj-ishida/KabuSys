CHANGELOG
=========
All notable changes to this project will be documented in this file.

フォーマットは「Keep a Changelog」に準拠します。

0.1.0 - 2026-03-21
------------------

Added
- 初回リリース: KabuSys Python パッケージの基本機能を実装。
- パッケージ概要
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 環境設定 / 設定読み込み (src/kabusys/config.py)
  - .env / .env.local ファイルおよび OS 環境変数から設定を自動読み込みする機能を実装。
  - 自動ロードの優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動読み込みを無効化可能（テスト用途を想定）。
  - .env パーサは以下に対応:
    - 空行・コメント行（#）の無視
    - export KEY=val 形式のサポート
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - クォートなし値におけるインラインコメントの扱い（直前が空白/タブの場合のみコメントとみなす）
  - Settings クラスにプロパティ化された設定値を提供（必須項目は未設定時に ValueError を送出）。
  - KABUSYS_ENV / LOG_LEVEL の検証（許容値は列挙済み）。

- データ取得・保存: J-Quants クライアント (src/kabusys/data/jquants_client.py)
  - J-Quants API 呼び出しユーティリティを実装（認証、ページネーション対応）。
  - レート制限対応: 固定間隔スロットリングで 120 req/min を守る RateLimiter を実装。
  - リトライロジック: 408/429/5xx 系に対する指数バックオフ（最大 3 回）。
  - 401 応答時の自動トークンリフレッシュ（1 回のみ）とトークンキャッシュを実装。
  - fetch_* 系関数（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）を提供（ページネーション対応）。
  - DuckDB への保存関数を実装（save_daily_quotes / save_financial_statements / save_market_calendar）。
    - INSERT は冪等性を保つため ON CONFLICT DO UPDATE を使用。
    - PK 欠損行はスキップしてログ出力。
  - 型変換ユーティリティ: _to_float / _to_int（入力の堅牢なパースを実現）。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を収集して raw_news に保存する機能を実装。
  - URL 正規化（スキーム・ホスト小文字化、トラッキングパラメータ除去、フラグメント除去、クエリソート）。
  - 記事 ID は正規化 URL の SHA-256 ハッシュ（先頭 32 文字）を使用して挿入の冪等性を保証。
  - defusedxml を用いた安全な XML パース（XML Bomb 等へ対策）。
  - HTTP(S) スキーム以外の URL を拒否して SSRF を軽減。
  - 受信サイズ上限（MAX_RESPONSE_BYTES = 10 MB）を設けメモリ DoS を防止。
  - DB バルク挿入はチャンク化（_INSERT_CHUNK_SIZE）して SQL 長・パラメータ上限に配慮。
  - デフォルト RSS ソースを一つ定義（Yahoo Finance のビジネスカテゴリ）。

- 研究用モジュール (src/kabusys/research/*.py)
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - Momentum（mom_1m, mom_3m, mom_6m, ma200_dev）を DuckDB の prices_daily から計算。
    - Volatility（atr_20, atr_pct, avg_turnover, volume_ratio）を計算。true_range の NULL 伝播を適切に制御。
    - Value（per, roe）を raw_financials と prices_daily から計算（report_date <= target_date の最新を使用）。
    - 計算は営業日ベースの窓長を想定し、データ不足時は None を返す設計。
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - 将来リターン計算 calc_forward_returns（複数ホライズン、SQL をまとめて実行）。
    - IC（Information Coefficient）計算 calc_ic（Spearman の ρ、同順位は平均ランクで処理）。
    - factor_summary（各ファクターの count/mean/std/min/max/median）と rank ユーティリティを提供。
  - 外部ライブラリに依存せず、DuckDB と標準ライブラリのみで動作する設計。

- 戦略層 (src/kabusys/strategy/*)
  - 特徴量エンジニアリング (src/kabusys/strategy/feature_engineering.py)
    - 研究環境で生成した生ファクターをマージ、ユニバースフィルタ適用、Zスコア正規化、±3でクリップした後に features テーブルへ日付単位で置換（冪等）。
    - ユニバースフィルタ: 株価 >= 300 円、20日平均売買代金 >= 5 億円。
    - DuckDB トランザクションで原子性を保証。
  - シグナル生成 (src/kabusys/strategy/signal_generator.py)
    - features と ai_scores を統合して final_score を算出し、BUY / SELL シグナルを生成して signals テーブルへ日付単位で置換（冪等）。
    - final_score は momentum/value/volatility/liquidity/news の重み付き合算（デフォルト重みを実装）。weights のバリデーションと合計が 1.0 でない場合の再スケール対応。
    - 欠損コンポーネントは中立値 0.5 で補完して不当な降格を防止。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数閾値以上）では BUY を抑制。
    - BUY 閾値デフォルト: 0.60。STOP-LOSS は -8%。
    - 保有ポジションのエグジット判定を実装（ストップロス、スコア低下）。SELL 優先ポリシー: SELL 対象を BUY から除外。
    - トランザクションで signals テーブルを更新し原子性を確保。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Security
- ニュース収集で defusedxml を使用して XML 脆弱性へ対策。
- RSS URL の正規化・スキームチェック・受信サイズ制限により SSRF やメモリ DoS のリスクを低減。
- J-Quants クライアントの HTTP エラー処理によりリトライやトークンリフレッシュを厳格化。

Notes / Known limitations
- シグナル生成における一部エグジット条件（トレーリングストップ、時間決済など）は実装されておらず、positions テーブルに peak_price / entry_date 等の追加データが必要。
- news_collector の説明にある「INSERT RETURNING による実際の挿入件数の正確な取得」は、現状は executemany ベースの実装になっている（DuckDB の INSERT RETURNING の利用は将来検討）。
- execution / monitoring パッケージは現時点でファイル存在のみ（実装は今後追加予定）。
- 一部の関数は DuckDB の特定テーブル（prices_daily, raw_financials, features, ai_scores, positions 等）に依存。これらのスキーマは外部での準備が必須。

Breaking Changes
- 初回リリースにつき該当なし。

Contributing
- 変更はこの CHANGELOG に追記してください。重大変更・破壊的変更は事前に議論の上で実施してください。

----- 
（このファイルはコードの実装内容をベースに推測して作成しています。実運用前に README / ドキュメントと合わせて設定項目、DB スキーマ、外部依存の確認を行ってください。）