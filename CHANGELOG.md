# Changelog

すべての重要な変更はこのファイルに記録します。本プロジェクトは Keep a Changelog に準拠します。  
変更はセマンティックバージョニングに従います。

- リリース日付は ISO 形式 (YYYY-MM-DD) で記載します。
- 主要なカテゴリ: Added, Changed, Deprecated, Removed, Fixed, Security

## [0.1.0] - 2026-03-31

初回リリース。日本株自動売買システムのコアライブラリを実装しました。主な追加内容は以下の通りです。

### Added
- パッケージ基盤
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。
  - 公開モジュール: data, strategy, execution, monitoring（__all__ 設定）。

- 設定・環境変数管理 (kabusys.config)
  - .env / .env.local 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で探索）。
  - export 形式やクォート・エスケープ・インラインコメントに対応した .env パーサ実装。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスで主要設定をプロパティ経由で取得:
    - J-Quants / kabuステーション / Slack / DB (DuckDB/SQLite) / 環境 (development/paper_trading/live) / ログレベル
  - 必須環境変数未設定時に ValueError を投げる _require 関数を提供。
  - 設定値のバリデーション（許容 env 値・ログレベルの検証）を実装。

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (news_nlp.py)
    - raw_news と news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini）へバッチ送信。
    - チャンクサイズ、記事数・文字数トリム、JSON Mode 応答のバリデーション実装。
    - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライ。
    - レスポンスのパース・スコアクリッピング（±1.0）、部分成功時の DB 書き換えロジック（DELETE → INSERT）を実装。
    - テスト用に内部の OpenAI 呼び出しを差し替え可能（unittest.mock.patch 用フック）。
    - タイムウィンドウ計算ユーティリティ calc_news_window を提供（JST→UTC の明示的変換、ルックアヘッド回避）。
  - 市場レジーム判定 (regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム判定（bull/neutral/bear）。
    - prices_daily / raw_news からフェイルセーフなデータ取得を行い、OpenAI 呼び出しのリトライや API エラー時のフォールバック（macro_sentiment=0.0）を実装。
    - レジーム計算はルックアヘッドバイアスを避ける設計（target_date 未満データのみ使用、datetime.today() を参照しない）。
    - 計算結果を market_regime テーブルへ冪等的に書き込む（BEGIN / DELETE / INSERT / COMMIT、失敗時 ROLLBACK）。

- データ処理・ETL (kabusys.data)
  - マーケットカレンダー管理 (calendar_management.py)
    - market_calendar を基にした営業日判定ユーティリティ群を実装:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB にデータがない場合は曜日ベースでフォールバック（週末休業）。
    - calendar_update_job を実装：J-Quants から差分取得して market_calendar を冪等更新、バックフィル・健全性チェック付き。
    - 検索上限（_MAX_SEARCH_DAYS）やバックフィル日数、先読みなどの安全設計。
  - ETL パイプライン (pipeline.py, etl.py)
    - ETLResult データクラスを実装（取得数・保存数・品質チェック・エラーの集約）。
    - 差分取得・backfill・品質検査の設計に基づく ETL 基盤を整備（jquants_client 経由の保存を想定）。
    - テーブル存在チェックや最大日付取得などの内部ユーティリティを提供。
    - kabusys.data.etl で pipeline.ETLResult を再エクスポート。
  - 互換性と DuckDB による実装：
    - DuckDB 接続を受け取り SQL と Python で処理する設計（外部DB依存最小化）。
    - DuckDB バージョン差異を考慮した executemany の空リストチェックや list バインド回避策を実装。

- リサーチ / ファクター (kabusys.research)
  - factor_research.py
    - Momentum, Value, Volatility, Liquidity など主要ファクター計算を実装:
      - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時 None）
      - calc_volatility: 20 日 ATR、ATR 比率、平均売買代金、出来高比率
      - calc_value: EPS/ROE から PER/ROE を算出（latest raw_financials を参照）
    - 各関数は prices_daily / raw_financials のみを参照し、本番取引APIにはアクセスしない。
    - Z スコア正規化ユーティリティを外部 data.stats として利用可能に想定。
  - feature_exploration.py
    - 将来リターン計算 (calc_forward_returns): 任意ホライズンに対する将来リターンを一括取得。
    - IC（Information Coefficient）計算 (calc_ic): スピアマンのランク相関を計算、データ足りない場合は None を返す。
    - rank, factor_summary: ランク変換（同順位は平均ランク）と基本統計量集計を実装。
    - Pandas 等に依存せず標準ライブラリ + DuckDB で実装。

### Changed
- 初回公開のため該当なし。

### Fixed
- 初回公開のため該当なし。

### Notes / 設計上の注記
- ルックアヘッドバイアス防止のため、日付依存処理はすべて呼び出し側が target_date を渡す方式を採用し、内部で datetime.today()/date.today() を参照しない実装方針。
- OpenAI クライアント呼び出しはモジュールごとに独立実装し、テスト時に差し替え可能な設計。
- DB 書き込みは可能な限り冪等性（DELETE→INSERT / ON CONFLICT 相当）を保つ設計。

---

今後のリリースでは以下を予定しています（例）:
- strategy / execution / monitoring モジュールの実装・統合テスト
- CI 上での DuckDB フィクスチャ・OpenAI モックテスト追加
- ドキュメント（API リファレンス、使用例）強化

もし CHANGELOG に追加してほしい詳細（例: 特定モジュールや設計決定の補足）があれば教えてください。