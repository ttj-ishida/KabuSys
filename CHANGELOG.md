# Changelog

すべての注記は Keep a Changelog の形式に準拠しています。  
このファイルはコードベースから推測して作成した変更履歴です。

- フォーマット: https://keepachangelog.com/ja/1.0.0/
- バージョン: 0.1.0（初回公開）

## [0.1.0] - 2026-04-02

Added
- パッケージ初期リリースを追加。
  - パッケージ名: kabusys、バージョン: 0.1.0
  - パッケージ公開時のトップレベル __all__ に data, strategy, execution, monitoring を設定。

- 環境設定モジュール (kabusys.config)
  - .env ファイルおよび環境変数の自動ロード機能を実装（プロジェクトルート検出: .git / pyproject.toml）。
  - .env、.env.local の読み込み順序・上書きルールを実装（OS 環境変数保護機能含む）。
  - export KEY=val 形式やクォート・エスケープ、インラインコメントのパースに対応。
  - 環境変数必須チェック関数 _require と Settings クラスを追加。
  - 設定項目例:
    - J-Quants / kabuステーション / Slack / DB パス（duckdb, sqlite） / 監視設定 (PID, CPU/Memory/Disk閾値)
    - 実行環境判定 (development/paper_trading/live)、ログレベル検証
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化対応。

- AI 系モジュール (kabusys.ai)
  - ニュース NLP (kabusys.ai.news_nlp)
    - raw_news + news_symbols から銘柄ごとの記事を集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いたバッチセンチメント評価を実装。
    - チャンク処理（最大 20 銘柄 / チャンク）、1銘柄あたり最大記事数・文字数制限、レスポンスバリデーション、スコアクリップ（±1.0）。
    - リトライ戦略（429/ネットワーク/タイムアウト/5xx は指数バックオフ）とフェイルセーフ（失敗時はスキップ・空辞書返却）。
    - calc_news_window (ニュース収集ウィンドウ計算) を提供。
    - score_news(conn, target_date, api_key=None) により ai_scores への冪等書き込みを実装（DELETE → INSERT をチャンクで実行）。
    - テスト容易性のため、OpenAI 呼び出し部分は差し替え可能（ユニットテスト用の patch を想定）。

  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース LLM センチメント（重み 30%）を合成して日次レジーム判定（bull/neutral/bear）を実装。
    - レジーム判定関数 score_regime(conn, target_date, api_key=None) を提供。計算結果を market_regime テーブルへ冪等書き込み。
    - LLM 呼び出しは個別実装、API 失敗時は macro_sentiment=0.0 で継続するフォールバックを採用。
    - リトライ・エラーハンドリング（RateLimit、接続エラー、タイムアウト、5xx など）を実装。

- データ基盤モジュール (kabusys.data)
  - カレンダー管理 (kabusys.data.calendar_management)
    - JPX カレンダーを管理する market_calendar 用ユーティリティを追加。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - DB にデータがない場合は曜日（平日/週末）ベースのフォールバックを行う設計。
    - calendar_update_job による J-Quants からの差分取得・バックフィル・保存ロジックを実装。最大探索日数・健全性チェックあり。

  - ETL パイプライン (kabusys.data.pipeline, kabusys.data.etl)
    - ETLResult データクラスを追加（取得数・保存数・品質問題・エラー集約）。
    - 差分更新・バックフィル・品質チェックを想定した設計（jquants_client 経由での保存、品質チェックモジュール integration を想定）。
    - kabusys.data.etl で ETLResult を公開再エクスポート。

  - jquants_client 経由の取得/保存フローと互換する設計方針を多数反映（差分取得、idempotent 保存、backfill）。

- リサーチ / ファクター計算 (kabusys.research)
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離率を計算（データ不足時の None 扱い）。
    - calc_volatility: 20 日 ATR（平均）、相対 ATR、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials からの EPS/ROE を組み合わせて PER/ROE を計算（EPS=0/欠損は None）。
    - DuckDB SQL を活用した高性能実装、ルックアヘッドバイアス防止を重視。

  - feature_exploration
    - calc_forward_returns: 指定ホライズンの将来リターンを一括で計算（horizons デフォルト [1,5,21]、入力検証あり）。
    - calc_ic: スピアマンランク相関（IC）を実装（結合/欠損排除/最小レコード数チェック）。
    - rank: 同順位は平均ランクで扱うランク計算ユーティリティ（丸め対策あり）。
    - factor_summary: 各カラムの count/mean/std/min/max/median を計算する統計サマリ機能。

- その他実装上の設計上の注意点（ドキュメント化）
  - ルックアヘッドバイアス防止: 各モジュールは datetime.today()/date.today() を直接参照せず、target_date 引数に依存する設計。
  - DuckDB を主なストレージとして想定し、SQL + Python の組み合わせで実装。
  - OpenAI (gpt-4o-mini) 統合は JSON Mode を想定し、レスポンスの堅牢なパース・検証ロジックを備える。
  - 各機能は DB 書き込み時に冪等性を考慮（DELETE→INSERT や ON CONFLICT を想定）し、失敗時は ROLLBACK を試みる。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Security
- （初期リリースのため該当なし）

Notes / Known limitations
- OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY に依存。未設定の場合は ValueError が発生する箇所がある（呼び出し側での設定が必要）。
- DuckDB バインドや executemany の空リスト挙動（DuckDB 0.10）に対する互換性考慮があるため、空パラメータ投入は回避している。
- raw_financials の PBR・配当利回りなど一部ファクターは未実装（今後拡張予定）。
- OpenAI 呼び出しの振る舞い（モデル名・JSON Mode）は将来の API 変化により調整が必要となる可能性あり。

--- 

今後のリリースでは、以下のような項目を想定しています（未実装／要検討）:
- strategy / execution / monitoring モジュールの具象実装とテスト
- jquants_client の具象実装と ETL の自動化ワークフロー
- 単体テスト・統合テストの追加（OpenAI 呼び出しのモックを含む）
- ドキュメント拡充（API リファレンス・運用手順・例）