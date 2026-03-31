# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このファイルはプロジェクトの変更点・実装済み機能をコードベースから推測して記載したものです。

文言:
- 「追加 (Added)」は新規実装機能や公開 API。
- 「変更 (Changed)」「修正 (Fixed)」「破壊的変更 (Breaking Changes)」は該当があれば記載。
- 日付は本ファイル作成日 (2026-03-31) を使用しています。

Unreleased
----------
- （現時点で未リリースの変更はありません）

[0.1.0] - 2026-03-31
-------------------

Added
- パッケージ基盤
  - 初期パッケージ公開: kabusys（__version__ = 0.1.0）。public API として data, research, ai などのサブパッケージをエクスポートする構成を採用。
- 環境設定 / 設定管理 (kabusys.config)
  - .env 自動ロード機能を実装（プロジェクトルートを .git / pyproject.toml から検出）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用途）。
  - .env パーサーの強化:
    - export KEY=val 形式対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理をサポート。
    - 無効行（空行・コメント・不正な行）をスキップ。
  - .env 読み込み時の上書き制御（override）と OS 環境変数保護（protected set）を実装。
  - Settings クラスを公開:
    - J-Quants / kabuステーション / Slack / DB パス / 監視閾値 / システム設定（env, log_level）など多数のプロパティを提供。
    - 必須環境変数未設定時は ValueError を投げる安全な取得メソッドを採用。
    - env 値の検証（development / paper_trading / live）や log_level 検証を実装。
- AI モジュール (kabusys.ai)
  - ニュースセンチメントスコアリング (kabusys.ai.news_nlp)
    - raw_news / news_symbols を集約し、銘柄ごとにニューステキストを組み合わせて OpenAI（gpt-4o-mini）の JSON モードでスコアを取得。
    - バッチ（最大20銘柄）単位の送信、1銘柄あたり記事数・文字数のトリム(_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK)を実装。
    - レスポンス検証とスコアの ±1.0 クリップ、JSON の前後ノイズを許容した復元処理を実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装。その他はスキップして継続するフォールバック方針。
    - テスト容易性のため _call_openai_api を差し替え可能に設計。
    - score_news(conn, target_date, api_key=None) を公開。書き込みは部分失敗に強い DELETE → INSERT の冪等処理。
    - calc_news_window(target_date) を公開（JST ウィンドウ計算、UTC naive datetime を返す）。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - prices_daily / raw_news を参照して ma200_ratio を計算し、マクロキーワードでフィルタした記事タイトルを LLM に投げる。
    - OpenAI 呼び出しは gpt-4o-mini を使用、JSON レスポンスをパースして macro_sentiment を算出。API 失敗時は macro_sentiment=0.0 を採用するフォールバック。
    - レジーム合成後、market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。DB 書き込み失敗時はロールバックを試み、上位に例外を送出。
    - テスト容易性のため _call_openai_api をモジュール別実装にしてモジュール間結合を抑制。
- データ基盤 (kabusys.data)
  - ETL パイプライン（kabusys.data.pipeline）
    - ETLResult データクラスを実装（取得数／保存数／品質課題／エラー等を集約）。
    - 差分更新・バックフィル・品質チェックを設計に明示。id_token 注入でテスト容易化。
    - DuckDB を利用したテーブル存在チェックや最大日付取得ユーティリティを実装（ETL 内部で使用）。
  - ETL の公開インターフェース（kabusys.data.etl）で ETLResult を再エクスポート。
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar を使った営業日判定 API を提供:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を実装。
    - market_calendar が未取得のときは曜日ベース（土日非営業）でフォールバックする堅牢なロジック。
    - next/prev_trading_day は最大探索日数上限を設けて無限ループを防止。
    - calendar_update_job を実装、J-Quants クライアントから差分取得して market_calendar に冪等保存（バックフィル・健全性チェックあり）。
    - J-Quants クライアント呼び出しは例外をキャッチして失敗時は 0 を返すフォールバック。
  - jquants_client の利用を想定（fetch / save 系関数を利用する設計）。
- リサーチ / ファクター群 (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算（データ不足時は None）。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算（データ不足時は None）。
    - calc_value: raw_financials から最新財務データを取得して PER / ROE を計算（EPS が 0 または欠損のときは None）。
    - DuckDB SQL ベースで効率的に計算、営業日・ウィンドウのバッファ設計あり。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算（有効件数 3 未満は None）。
    - rank: 同順位は平均ランクとするランク化処理（浮動小数の丸め対策あり）。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリー。
  - research パッケージは主要関数を再エクスポートして公開（calc_momentum, calc_value, calc_volatility, zscore_normalize など）。
- ロギング・監視関連（設定側）
  - Settings に CPU/メモリ/ディスク閾値や PID ファイルパスを追加（監視用途）。

Security
- 環境変数の読み込みで OS 環境変数の上書きを制限する protected 機構を導入（.env からの意図しない上書きを防ぐ）。

Fixed
- （初期リリースのため特定の修正履歴はなし。想定されるエラー処理・フォールバックを多めに実装している）

Changed
- （初回公開のため該当なし）

Breaking Changes
- （初回リリースのため該当なし）

Notes / 実装上の重要な挙動
- OpenAI API を使う機能（news_nlp, regime_detector）は API キー必須。api_key を引数で渡すか、環境変数 OPENAI_API_KEY を設定する必要がある。未設定時は ValueError を送出。
- LLM 呼び出し失敗時は「スキップして継続」するフェイルセーフ設計（スコアのフォールバック値を利用）。そのため LLM の一時障害が ETL 全体を停止させない。
- 日付計算は明示的に date / datetime を受け取り、datetime.today()/date.today() の直接参照を避ける（ルックアヘッドバイアス対策）。
- DuckDB のバージョン依存（executemany の空リスト不可等）に配慮した実装を行っている。

今後の TODO（コードから推測）
- strategy / execution / monitoring パッケージの実装（__all__ に含まれているが今回のスナップショットには実装がない）。
- 追加の品質チェックルールや監視アラート発火ロジックの実装。
- 単体テストと CI におけるモック戦略の整備（OpenAI, J-Quants クライアント等の差し替え）。

もし CHANGELOG の粒度（より細かい変更履歴、コミット単位の記載、日付の正確化など）を希望される場合は、コミットログやリリース履歴を提供してください。