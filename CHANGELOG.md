# CHANGELOG

すべての注目すべき変更を記録します。本ファイルは「Keep a Changelog」形式に準拠しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
- （なし）

## [0.1.0] - 2026-03-29
初回リリース。日本株の自動売買・データ基盤・リサーチ向けのコアライブラリ群を提供します。主な追加内容は以下の通りです。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージ初版を追加。__version__ = "0.1.0"。
  - パッケージ外部公開モジュール: data, strategy, execution, monitoring（__all__ を設定）。

- 設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装（プロジェクトルートは `.git` または `pyproject.toml` を基準に検出）。
  - .env/.env.local の読み込み順序と上書きルールを実装。OS 環境変数を保護する protected 機能を提供。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env のパースは export プレフィックス、シングル／ダブルクォート、エスケープ、インラインコメントなどに対応。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス等の設定取得プロパティを実装。
  - KABUSYS_ENV（development/paper_trading/live）および LOG_LEVEL のバリデーションを追加。

- AI（ニュース解析 / レジーム判定）
  - ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news と news_symbols を集約して銘柄ごとのニュースを作成し、OpenAI（gpt-4o-mini, JSON mode）へバッチで送信してセンチメント（-1.0〜1.0）を取得。
    - バッチサイズ、記事数・文字制限、429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライを実装。
    - レスポンスのバリデーション、スコアクリップ、DuckDB への冪等的な書き込み（DELETE → INSERT）を実装。
    - テスト用に _call_openai_api をパッチ可能にして差し替えを想定。
    - calc_news_window ユーティリティにより JST ベースのニュース収集ウィンドウを正確に算出。

  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して market_regime テーブルに日次で書き込み。
    - LLM 呼び出しは gpt-4o-mini を使用、JSON レスポンスを想定。API エラーやパース失敗は macro_sentiment=0.0 でフォールバック（フェイルセーフ）。
    - DuckDB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）と ROLLBACK の安全処理を実装。
    - ルックアヘッドバイアス防止のため、date 引数を用いた処理を徹底（datetime.today()/date.today() を直接参照しない設計）。

- データ基盤 (src/kabusys/data)
  - カレンダー管理 (src/kabusys/data/calendar_management.py)
    - market_calendar テーブルに基づく営業日判定ユーティリティを提供（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB 未取得時の曜日ベースフォールバック、未登録日の取り扱い、一貫した振る舞いを実装。
    - 夜間バッチ更新 job（calendar_update_job）で J-Quants から差分取得して保存するフローを実装。バックフィル、健全性チェック（将来日付の異常検出）を組み込み。
    - market_calendar がまばらにしかない場合でも次/前営業日計算が一貫するよう設計。

  - ETL パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult データクラスを定義し、ETL 実行結果（取得件数、保存件数、品質問題、エラー等）を集約。
    - 差分更新、バックフィル、品質チェックの設計方針を反映したユーティリティを実装（詳細な ETL 実行ロジックは jquants_client / quality モジュールと連携）。
    - etl モジュールで pipeline.ETLResult を再エクスポート。

  - jquants_client（参照）との idempotent な保存（ON CONFLICT DO UPDATE）想定。

- リサーチ（ファクター計算・特徴量探索）
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離の計算（データ不足時の扱いを明確化）。
    - Volatility: 20 日 ATR、ATR の相対値、20 日平均売買代金、出来高比率を実装。true_range の NULL 伝播制御を実装。
    - Value: raw_financials から最新の財務データを取得し PER / ROE を計算（EPS が 0 または欠損時は None）。
    - DuckDB を用いた SQL で高効率に計算し、(date, code) ベースの結果リストを返却。

  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - 将来リターン計算（calc_forward_returns）: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを計算。ホライズン検証（1〜252）を実装。
    - IC（calc_ic）: factor_records と forward_records を code で結合し、スピアマンランク相関（ランクは同順位平均）を計算。
    - rank, factor_summary: ランク変換（同順位を平均ランク）とファクターの統計サマリー（count/mean/std/min/max/median）を提供。
    - pandas 等の外部依存を持たない純粋 Python 実装。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- 初回リリースのため該当なし。

### 設計上の注意点・既知の動作
- OpenAI 統合は gpt-4o-mini と JSON Mode を前提としている。API キーは関数引数で注入可能（テスト容易性）か、環境変数 OPENAI_API_KEY を利用。
- LLM 呼び出し失敗時は例外を投げずにフォールバックする設計の箇所があり（ニュース/レジーム系は 0.0 フォールバック）、これにより自動化パイプラインの耐障害性を確保。
- DuckDB への書き込みは明示的にトランザクション管理（BEGIN/COMMIT/ROLLBACK）を行い、部分失敗時に既存データを保護する処理を実装。
- 日付取扱いはすべて date/datetime（タイムゾーン混入を避ける）で統一。ルックアヘッドバイアス防止のため、現時刻参照は関数外に露出せず、target_date を明示的に渡す設計。
- テスト容易性のため、OpenAI 呼び出し等の内部関数はモック差し替えを想定している（unittest.mock.patch で置換可能）。

---

今後のリリースでは、strategy / execution / monitoring モジュールの具備、jquants_client の具体実装連携、より詳細な品質チェック・メトリクス、ドキュメントやサンプル ETL ワークフローの追加を予定しています。変更履歴は今後のリリースごとに更新します。