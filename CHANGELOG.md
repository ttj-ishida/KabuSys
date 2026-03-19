# Changelog

すべての注記は Keep a Changelog の形式に準拠します。  
このファイルはコードベース（初期実装）から推測した変更履歴を日本語でまとめたものです。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

- なし。

## [0.1.0] - 2026-03-19

初回リリース（初期実装）。以下の主要機能とモジュールを実装・追加しました。

### 追加 (Added)

- パッケージ基本情報
  - パッケージ名: kabusys、バージョン 0.1.0。

- 設定 / 環境変数管理 (src/kabusys/config.py)
  - .env / .env.local ファイルを自動ロードする仕組み（プロジェクトルートの検出は .git または pyproject.toml に基づく）。
  - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサー: export プレフィックス対応、クォート／エスケープ対応、インラインコメント処理、無効行スキップ。
  - .env 上書き制御: override と protected キーの概念（OS 環境変数保護）。
  - Settings クラス: J-Quants トークン、kabu API、Slack、DB パス、環境（development/paper_trading/live）やログレベルの検証ユーティリティを提供。
  - 必須環境変数未設定時は明示的な例外を投げる _require()。

- データ取得・保存 (src/kabusys/data/)
  - J-Quants クライアント (jquants_client.py)
    - API 呼び出し用の共通 _request 実装（JSON デコード検証、例外ハンドリング）。
    - レート制御: 固定間隔スロットリングで 120 req/min を守る _RateLimiter。
    - 再試行ロジック: 指数バックオフ、最大 3 回、408/429/5xx をリトライ対象。
    - 401 Unauthorized 受信時は ID トークンを自動リフレッシュして 1 回リトライ（無限再帰を防止）。
    - ページネーション対応（pagination_key）。
    - ID トークンのモジュールレベルキャッシュ（ページネーション間で共有）。
    - データ取得関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
    - DuckDB へ冪等保存する関数: save_daily_quotes, save_financial_statements, save_market_calendar（ON CONFLICT / DO UPDATE を利用）。
    - データ型変換ユーティリティ: _to_float, _to_int（堅牢なパースを行い不正値は None に変換）。

  - ニュース収集モジュール (news_collector.py)
    - RSS フィードから記事を収集し raw_news に冪等保存する処理。
    - URL 正規化: 小文字化、トラッキングパラメータ（utm_*, fbclid 等）除去、フラグメント削除、クエリソート。
    - 記事 ID は正規化 URL の SHA-256 ハッシュ（先頭 32 文字）を生成して冪等性を担保。
    - defusedxml を利用した XML パーシング（XML Bomb 等対策）。
    - HTTP レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）や SSRF 緩和の考慮。
    - バルク INSERT をチャンク化して DB へ保存、INSERT RETURNING を用いた正確な挿入数把握。

- 研究・ファクター計算 (src/kabusys/research/)
  - factor_research.py
    - Momentum: mom_1m, mom_3m, mom_6m、ma200_dev（200日移動平均乖離率）を計算。
    - Volatility: 20日 ATR（atr_20）, 相対 ATR (atr_pct), 20日平均売買代金 (avg_turnover), volume_ratio を計算。
    - Value: per (price / EPS), roe を計算（raw_financials の最新レコードを使用）。
    - 各計算は DuckDB の SQL ウィンドウ関数を活用し、営業日欠損（祝日等）に対応するためのスキャン範囲バッファを導入。
  - feature_exploration.py
    - 将来リターン計算 (calc_forward_returns): 複数ホライズン（デフォルト [1,5,21]）に対応。
    - IC（Information Coefficient）計算 (calc_ic): スピアマンのランク相関を実装（ties は平均ランクで処理）。
    - factor_summary: count/mean/std/min/max/median を算出。
    - rank: 同順位を平均ランクで扱う実装（浮動小数の丸めで ties 検出を安定化）。

  - research パッケージのエクスポートを整理。

- 戦略 (src/kabusys/strategy/)
  - feature_engineering.py
    - 研究環境で計算した生ファクターを統合し features テーブルへ保存する build_features を実装。
    - ユニバースフィルタ（株価 >= 300 円、20日平均売買代金 >= 5 億円）。
    - Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）、±3 でクリップ。
    - 日付単位で既存レコードを削除してから挿入することで冪等性と原子性を確保（BEGIN/COMMIT, ROLLBACK 順守）。
  - signal_generator.py
    - features と ai_scores を統合して final_score を算出し BUY / SELL シグナルを生成する generate_signals を実装。
    - デフォルト重みの定義（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）とユーザ重みの検証・スケーリング。
    - シグナル生成フロー: AI レジーム判定（Bear の場合 BUY を抑制）、コンポーネントスコア計算（モメンタム・バリュー・ボラティリティ・流動性・ニュース）、None の補完は中立値 0.5。
    - SELL 条件の実装（ストップロス: -8%、スコア低下）と未実装条件の明示（トレーリングストップ、時間決済）。
    - 保有銘柄の価格欠損時は SELL 判定をスキップして誤クローズを防止。
    - signals テーブルへの日付単位置換で原子性を確保。

- パッケージ公開 API
  - strategy モジュールで build_features / generate_signals を __all__ で公開。
  - research パッケージで主要ユーティリティをエクスポート。

### 変更 (Changed)

- 初回リリースのため該当なし。

### 修正 (Fixed)

- 初回リリースのため該当なし。

### 既知の制限・注意点 (Known issues / Notes)

- signal_generator のいくつかのエグジット条件（トレーリングストップ、時間決済）は未実装。positions テーブルに peak_price / entry_date 等のカラムが必要。
- research モジュールは DuckDB の prices_daily / raw_financials の存在を前提とする。データ整備が必要。
- jquants_client の _request は urllib を使用した同期実装。大量データ収集時は実行時間・スループットの考慮が必要。
- news_collector は RSS の多様なフォーマットに対応するための追加ハンドリング（エンコーディング、メディアコンテンツ抽出など）が今後必要になる可能性あり。
- 環境変数の自動ロードはプロジェクトルートが検出されない場合スキップされる（ライブラリ配布後の挙動に配慮）。

### セキュリティ / 安全設計上の考慮

- news_collector で defusedxml を使用し XML 攻撃を軽減。
- ニュース取得時の URL 正規化とトラッキングパラメータ除去により冪等化とトラッキング漏れを低減。
- J-Quants クライアントでトークン自動リフレッシュ・再試行・レート制御を実装し API 利用の安全性と堅牢性を向上。
- .env の読み込みで既存 OS 環境変数を保護するための protected 機構を導入。

---

作成にあたってはコード内のドキュメント文字列と実装内容から機能・設計意図を推測しています。実際の変更履歴が必要な場合は、ソース管理のコミットログ（git log）を参照してください。