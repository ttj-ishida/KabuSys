Keep a Changelog に準拠した CHANGELOG.md（日本語）を以下に作成しました。

保持方針・フォーマットの説明リンク等は省略せず冒頭に一行だけ記載しています（必要であれば削除してください）。

KEEP A CHANGELOG — kabusys

All notable changes to this project will be documented in this file.

Unreleased
---------
（なし）

[0.1.0] - 2026-03-29
-------------------
Added
- 初期リリース: kabusys パッケージ v0.1.0 を追加。
  - パッケージ公開情報: src/kabusys/__init__.py に __version__ = "0.1.0" と __all__ のエクスポートを追加。

- 環境設定/管理
  - 環境変数・設定読み込みモジュールを追加（src/kabusys/config.py）。
    - .env/.env.local の自動読み込み（プロジェクトルート検出: .git または pyproject.toml）。
    - export KEY=val 形式・シングル/ダブルクォート・エスケープ・インラインコメント等を考慮した堅牢な .env 解析。
    - OS 環境変数の保護（既存キーを protected として上書き防止）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプション。
    - Settings クラスを提供し、J-Quants / kabuAPI / Slack / DB パス / 環境種別等のプロパティを環境変数から取得。値検証（KABUSYS_ENV, LOG_LEVEL）とユーティリティ（is_live 等）を実装。
    - 必須環境変数未設定時は ValueError を発生させる _require 実装。

- AI ニュース/NLP（OpenAI 統合）
  - ニュースセンチメント分析モジュールを追加（src/kabusys/ai/news_nlp.py）。
    - ニュース収集ウィンドウ計算（JST ベース → UTC ナイーブ datetime） calc_news_window。
    - raw_news と news_symbols を銘柄ごとに集約し、銘柄単位で最大記事数・文字数をトリムして OpenAI（gpt-4o-mini）へバッチ送信（チャンクサイズ: 最大 20 銘柄）。
    - 再試行戦略: 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ（リトライ設定）。
    - OpenAI JSON Mode のレスポンスを堅牢にパース・バリデーション（余計な前後テキストが混在する場合の {} 抽出含む）。
    - スコアを ±1.0 にクリップし、ai_scores テーブルへ冪等的に（DELETE → INSERT）書き込み。部分失敗時に他銘柄の既存スコアを保護する挙動を実装。
    - テスト容易化のため _call_openai_api を patch 可能に設計。

  - 市場レジーム判定モジュールを追加（src/kabusys/ai/regime_detector.py）。
    - ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - prices_daily からの ma200_ratio 計算、raw_news のマクロキーワードフィルタ、OpenAI 呼び出し、スコア合成、market_regime テーブルへの冪等書き込みを実装。
    - API エラー時のフェイルセーフ: macro_sentiment = 0.0 をフォールバック。
    - OpenAI 呼び出しに対するリトライ・バックオフ、500 系判定などを考慮した堅牢な実装。
    - テスト用に _call_openai_api の差し替えを想定。

- 研究（Research）ユーティリティ
  - ファクター計算と特徴量探索モジュールを追加（src/kabusys/research/*）。
    - factor_research.py:
      - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足時は None を返す設計。
      - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率等を計算。
      - calc_value: raw_financials から最新の財務データを取得して PER/ROE を算出（EPS が 0/欠損の場合は None）。
      - DuckDB を使った SQL ベース計算により外部 API へはアクセスしない安全な算出。
    - feature_exploration.py:
      - calc_forward_returns: 将来リターン（任意の horizon、デフォルト [1,5,21]）を一括取得する効率的実装。
      - calc_ic: スピアマンのランク相関（IC）を計算。有効レコード数が少ない場合は None を返す。
      - rank / factor_summary: ランク変換（同順位は平均ランク）、基本統計量（count/mean/std/min/max/median）を算出。
    - zscore_normalize は data.stats から再エクスポート（research パッケージ初期化に含む）。

- データ基盤（Data）
  - calendar_management.py:
    - JPX カレンダー管理: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を実装。
    - market_calendar テーブルが未取得の場合の曜日ベースフォールバック（週末を非営業日扱い）。
    - calendar_update_job: J-Quants から差分取得 → market_calendar へ冪等保存（バックフィル・健全性チェック含む）。
    - 検索範囲上限（_MAX_SEARCH_DAYS）による無限ループ防止、date オブジェクトの一貫利用等の設計方針を反映。

  - ETL / pipeline（src/kabusys/data/pipeline.py / etl.py）
    - ETLResult dataclass を実装し ETL の結果情報（取得数・保存数・品質問題・エラー）を集約可能に。
    - 差分更新向けユーティリティ（_get_max_date 等）を実装。
    - J-Quants クライアント経由の差分取得・保存・品質チェックフローに沿った設計を反映。
    - etl モジュールから ETLResult を再エクスポート。

- 内部の堅牢性・テスト性向上
  - DuckDB の executemany が空リストを許容しない点への対応（空時のスキップ）。
  - レスポンスパース失敗や API エラーを例外にせずログとフォールバックで継続する設計（フェイルセーフ）。
  - ルックアヘッドバイアス防止のため datetime.today()/date.today() を直接参照しない実装方針（target_date を明示的に受け取る API）。
  - OpenAI 呼び出し関数のモジュール間結合を避け、各モジュールで独立実装（テストで差し替えやすい）。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Security
- 環境変数自動ロード時に OS 環境変数を上書きしない保護ロジックを導入（protected set）。
- 自動 .env ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD により明示的に無効化可能。

Notes / Migration
- OpenAI API キーは関数引数 api_key または環境変数 OPENAI_API_KEY で解決。未設定の場合は ValueError を送出するため、実行前にキー設定が必要。
- DuckDB テーブル構成（raw_news / news_symbols / ai_scores / prices_daily / market_calendar / raw_financials など）に依存しているため、実行前にスキーマ/データを用意すること。
- AI モジュールは外部 API（OpenAI）に依存するため、課金・レート制限・API 変更に注意。テスト時は _call_openai_api をモックすることを推奨。

開発者向け備考
- 主要な定数（バッチサイズ、リトライ回数、ウィンドウ幅、最大記事数など）はソース内で定義されており、要件に応じて調整可能。
- ログは各モジュールで logger を取得して出力しているため、アプリ全体のログ設定（ハンドラ・レベル）は呼び出し側で統一的に設定してください。

（以上）