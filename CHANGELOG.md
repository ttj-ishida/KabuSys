CHANGELOG
=========

すべての重要な変更点は Keep a Changelog の形式に従って記録しています。  
このファイルは人間と自動化ツールの両方で読みやすいことを目指しています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- 今のところ未リリースの変更はありません。

[0.1.0] - 2026-03-27
-------------------

初回リリース。日本株自動売買システム "KabuSys" の基盤機能を提供します。

Added
- パッケージ情報
  - kabusys パッケージ初期化 (src/kabusys/__init__.py)
    - バージョン: 0.1.0
    - 公開モジュール: data, strategy, execution, monitoring

- 環境設定 / .env 管理 (src/kabusys/config.py)
  - .env / .env.local の自動読み込み機能を実装
    - 読み込み優先度: OS環境変数 > .env.local > .env
    - OSの既存環境変数を保護する protected 機構
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能
  - .env の行パーサを実装
    - export KEY=val 形式対応
    - シングル/ダブルクォート、バックスラッシュエスケープ対応
    - インラインコメントの扱い（クォート有無による違い）に対応
  - Settings クラスを提供（環境変数から安全に値を取得）
    - J-Quants / kabuステーション / Slack / データベースパス / システム設定等のプロパティ
    - KABUSYS_ENV, LOG_LEVEL のバリデーション（許容値チェック）
    - duckdb/sqlite パスの expanduser 処理
    - 必須環境変数未設定時は ValueError を発生

- AI モジュール (src/kabusys/ai)
  - ニュースNLP スコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news と news_symbols を元に銘柄ごとのニュースを集約して OpenAI（gpt-4o-mini）の JSON mode でセンチメント評価
    - タイムウィンドウ（前日15:00 JST ～ 当日08:30 JST）計算ユーティリティ calc_news_window を実装
    - バッチ処理（_BATCH_SIZE=20）・チャンク毎のスコア取得・最大トークン肥大対策（記事数・文字数トリム）
    - リトライ戦略（429/ネットワーク断/タイムアウト/5xx に対する指数バックオフ）
    - レスポンス検証（JSONパース、"results" 構造、コード照合、数値チェック）と ±1.0 でのクリップ
    - 成功分のみ ai_scores テーブルへ冪等更新（DELETE → INSERT、部分失敗時に既存データ保護）
    - テスト容易性のため OpenAI 呼び出し関数を差し替え可能に設計
  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321（日経225連動型）の200日移動平均乖離（MA 比率）とマクロニュースの LLM センチメントを重み合成して日次レジーム判定
      - 重み: MA70% / マクロ30%、MA スケール補正あり（_MA_SCALE）
      - クリップ: -1.0〜1.0、閾値に応じて 'bull' / 'neutral' / 'bear' を割り当て
    - マクロニュース抽出、OpenAI 呼び出し（gpt-4o-mini）、再試行ロジック、フェイルセーフ（API障害時 macro_sentiment=0.0）
    - duckdb の prices_daily / raw_news を参照し market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）
    - テストでの差し替えを想定した設計（_call_openai_api をモック可能）

- Research モジュール (src/kabusys/research)
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - calc_momentum: mom_1m/mom_3m/mom_6m と 200日MA乖離（ma200_dev）を計算
      - データ不足時は None を返す、安全に扱える実装（window バッファあり）
    - calc_volatility: 20日 ATR（atr_20/atr_pct）、20日平均売買代金、出来高比率を計算
      - true_range の NULL 伝播を制御して正確に ATR を集計
    - calc_value: raw_financials から最終財務データを取得し PER / ROE を算出（EPSが0/NULLのときは None）
    - DuckDB を用いたウィンドウ関数中心の SQL 実装、外部 API への依存なし
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得
    - calc_ic: ファクターと将来リターンのランク相関（Spearman ρ）を実装（3件未満で計算不可）
    - rank: 平均ランク（同順位は平均）を返す実装（丸めによる ties 対応）
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリ

- Data モジュール (src/kabusys/data)
  - カレンダー管理 (src/kabusys/data/calendar_management.py)
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days 等の営業日ユーティリティ
      - market_calendar テーブルがある場合は DB 値優先、未登録日は曜日ベースでフォールバック
      - 最大探索日数制限 (_MAX_SEARCH_DAYS) による無限ループ防止
    - calendar_update_job: J-Quants API（jquants_client.fetch_market_calendar）から差分取得して market_calendar を冪等で更新
      - バックフィル（直近 _BACKFILL_DAYS 日）と健全性チェック（過度な将来日付はスキップ）
  - ETL / パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult データクラス（取得数・保存数・品質問題・エラーの記録、ヘルパーメソッド含む）
    - 差分取得のためのユーティリティ（テーブル存在確認、最大日付取得）
    - jquants_client および quality モジュールを用いた idempotent 保存と品質チェックを想定
    - data.etl で ETLResult を再エクスポート

Changed
- 初回リリースのため過去からの変更はありません。

Fixed
- 初回リリースのため修正履歴はありません。

Security
- 初回リリースのためセキュリティ関連の既知の修正はありません。

Breaking Changes
- 初回リリースなので破壊的変更はありません。ただし将来 Settings の環境変数名や public API を変更する場合はメジャーバージョンでの互換性保証方針に従う予定です。

Notes / Implementation details
- DuckDB を主要なストレージ層として利用（関数は DuckDB 接続を引数に取る設計）
- OpenAI を用いる箇所はモデル gpt-4o-mini を想定し、JSON Mode を利用して厳密な構造を受け取る設計
- ルックアヘッドバイアス対策として datetime.today()/date.today() を直接参照せず、すべて呼び出し側が target_date を提供する方式を採用
- ロギングを多用し、API エラーはフェイルセーフにより局所的にフォールバック（例: macro_sentiment=0.0）して全体処理を継続する方針

作者・貢献
- ソースコード内の docstring に設計方針や注意点を多く含めています。ユニットテスト用に OpenAI 呼び出し等をモック可能にしてあるため、テストの追加が容易です。

--- 

注: この CHANGELOG はコードベースの現在の内容から推測して作成しています。将来のコミットでは各変更点をこのファイルに追記してください。