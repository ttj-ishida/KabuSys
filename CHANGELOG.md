CHANGELOG
=========

すべての変更は Keep a Changelog の方針に準拠して記載しています。主要なカテゴリは Added / Changed / Fixed / Removed / Security です。

Unreleased
----------

- なし

0.1.0 - 2026-03-28
------------------

Added
- パッケージ初期リリース。モジュール構成:
  - kabusys.config: 環境変数/設定管理
    - .env 自動読み込み機能（プロジェクトルートは .git または pyproject.toml を基準に探索）
    - .env / .env.local の読み込み順序（OS 環境変数 > .env.local > .env）
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを無効化可能
    - .env パーサは export フォーマット・シングル/ダブルクォート・エスケープ・コメント処理に対応
    - Settings クラスを提供（J-Quants / kabuステーション / Slack / DB パス / 環境・ログレベルのバリデーション）
  - kabusys.ai:
    - news_nlp.score_news
      - raw_news / news_symbols から前日15:00 JST〜当日08:30 JST に相当する記事を抽出（UTC に変換）
      - 銘柄ごとに記事を集約（最大記事数・文字数でトリム）
      - OpenAI（gpt-4o-mini、JSON Mode）へバッチ送信（チャンクサイズ 20）
      - 429/ネットワーク/タイムアウト/5xx をエクスポネンシャルバックオフでリトライ
      - レスポンス検証とスコア ±1.0 でクリップ、ai_scores テーブルへ冪等的に置換（DELETE → INSERT）
      - テスト用フック: _call_openai_api の差し替えでモック可能
    - regime_detector.score_regime
      - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次市場レジーム（bull/neutral/bear）を判定
      - マクロキーワードで raw_news をフィルタしてタイトルを抽出、OpenAI へ送信（gpt-4o-mini）
      - API 呼び出しはリトライ付き、失敗時は macro_sentiment=0.0 のフェイルセーフ
      - レジーム結果を market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）
      - テスト用フック: _call_openai_api の差し替えでモック可能
  - kabusys.data:
    - calendar_management
      - market_calendar に基づく営業日判定ユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）
      - DB が未取得/未登録の場合は曜日ベースのフォールバック（週末は休場）
      - calendar_update_job: J-Quants API から差分取得・バックフィル（直近 N 日を再フェッチ）・健全性チェック・保存処理を実装
    - pipeline / etl
      - ETLResult データクラス（ETL 実行結果と品質チェック結果の集約）
      - 差分更新・バックフィル・品質チェックを想定したユーティリティ（最終取得日の取得など）
    - etl の再エクスポートインターフェース（ETLResult を公開）
  - kabusys.research:
    - factor_research
      - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算（データ不足時は None）
      - calc_volatility: 20 日 ATR、ATR 比率、平均売買代金、出来高比率を計算（データ不足時は None）
      - calc_value: raw_financials から EPS/ROE を組み合わせて PER/ROE を算出
      - SQL + DuckDB ウィンドウ関数で高性能に実装、外部 API に依存しない
    - feature_exploration
      - calc_forward_returns: 任意ホライズン（デフォルト 1,5,21 営業日）の将来リターン計算
      - calc_ic: スピアマンランク相関（IC）計算（3 銘柄未満で計算不能の場合は None を返す）
      - rank: 同順位は平均ランクで扱う安定化済みランク関数
      - factor_summary: count/mean/std/min/max/median を標準ライブラリのみで計算
  - その他
    - DuckDB をメインのローカル DB として利用する設計（各モジュールは DuckDB 接続を受け取る）
    - ロギングと例外取り扱いを各所に実装（DB 書き込みでの BEGIN/COMMIT/ROLLBACK 保護、失敗時の WARN/INFO/EXCEPTION ログ）
    - テスト容易性を考慮した設計（API 呼び出しの差し替えポイントや自動 env ロードの抑止）

Changed
- 初回リリースのため該当なし

Fixed
- 初回リリースのため該当なし

Removed
- 初回リリースのため該当なし

Security
- 初回リリースのため該当なし

Notes / 実装上の重要な決定
- ルックアヘッドバイアス防止:
  - AI スコアやレジーム判定で datetime.today()/date.today() を直接参照しない設計（すべて caller が target_date を明示的に渡す）
  - DB クエリでは date < target_date や半開区間を使って未来データの混入を防止
- フェイルセーフ:
  - OpenAI API の失敗はスコア 0.0 やスキップで継続し、ETL/スコア処理の全体停止を防ぐ設計
- idempotency:
  - market_regime / ai_scores / 各 save_* は既存データを削除してから挿入する等、冪等性を考慮
- テストフレンドリー:
  - _call_openai_api の差し替えで外部 API をモック可能
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で .env 自動ロードを抑制可能

今後の改善候補（未実装・設計メモ）
- ai モデルの切替・モデル設定の外部化（現在は gpt-4o-mini 固定）
- ai スコアの追跡・監査ログ強化（リクエスト/レスポンスの安全な保存）
- ETL の並列化・進捗管理 UI
- ファクターの追加（PBR、配当利回り等）およびバックテスト統合

--- 

（注）日付はソースコードの最終更新日・現行日を元に推定しています。実際のリリース管理では Git のタグ/コミットログやリリース日付をご利用ください。