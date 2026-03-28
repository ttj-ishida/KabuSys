# Changelog

すべての重要な変更はこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠します。
リリース日はソースコードの最終更新を基にしています。

- リリースの指針: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-03-28

初回公開リリース。日本株自動売買・データ基盤・リサーチ・AI支援の各機能を含むモジュール群を提供します。

### 追加 (Added)
- パッケージ基盤
  - パッケージ名: kabusys、バージョン 0.1.0 を定義（src/kabusys/__init__.py）。
  - 公開モジュール群: data, research, ai, execution, strategy, monitoring（__all__ に準備）。

- 環境設定・ロード機能（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定をロードする自動ローダーを実装。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - プロジェクトルート検出は __file__ を基点に .git または pyproject.toml を探索（CWD 非依存）。
  - .env パーサを実装（export プレフィックス、クォート文字列、インラインコメント処理、エスケープ対応）。
  - Settings クラスを提供（J-Quants / kabu / Slack / DB パス / 環境種別 / ログレベル等のプロパティ）。
  - 必須環境変数未設定時は ValueError を送出する _require ユーティリティを実装。

- AI モジュール（src/kabusys/ai）
  - news_nlp モジュール（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini）によりセンチメントを算出。
    - タイムウィンドウ計算（JSTベース → UTC換算）を提供（calc_news_window）。
    - バッチ処理（最大 20 銘柄／コール）、トークン肥大化対策（記事数・文字数制限）。
    - リトライ（429・ネットワーク・タイムアウト・5xx に対する指数バックオフ）、レスポンス検証、スコア ±1.0 クリップ。
    - DuckDB への冪等書き込み（DELETE → INSERT）を実施。部分失敗時に既存スコアを保持する設計。
    - テスト容易性のため OpenAI 呼び出し箇所は差し替え可能（_call_openai_api をモック可能）。
  - regime_detector モジュール（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動）の200日移動平均乖離（重み 70%）と、ニュース由来のマクロセンチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定。
    - マクロニュース抽出はマクロキーワードリストでフィルタし、LLM に送信してスコア化。
    - LLM 呼び出しのリトライ・フェイルセーフ実装（APIエラー時は macro_sentiment=0.0）。
    - DuckDB へ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実施。
    - ルックアヘッドバイアス防止のため日付の扱いに注意（datetime.today() を参照しない設計）。

- データプラットフォーム（src/kabusys/data）
  - calendar_management モジュール
    - JPX カレンダー（market_calendar）の管理と夜間バッチ更新（calendar_update_job）。
    - 営業日判定ユーティリティ群: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB にデータが無い場合は曜日ベースのフォールバック（週末を休日扱い）。
    - 最大探索日数を設定して無限ループを回避。
  - pipeline / etl 周り（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラスを公開（ETL の集計結果、品質問題、エラー一覧を格納）。
    - 差分取得・バックフィル・保存・品質チェックを想定した設計。jquants_client と quality モジュールと協調。
    - DB テーブル最大日付取得等のユーティリティ実装。
  - data パッケージから ETLResult を再エクスポート。

- リサーチ機能（src/kabusys/research）
  - factor_research（src/kabusys/research/factor_research.py）
    - モメンタム（1M/3M/6M リターン、ma200 乖離）、ボラティリティ（20日 ATR）、流動性（平均売買代金、出来高比率）、バリュー（PER/ROE）を計算する関数群:
      - calc_momentum, calc_volatility, calc_value
    - DuckDB の SQL ウィンドウ関数を利用して効率的に集計。データ不足時の None ハンドリング。
  - feature_exploration（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns、複数ホライズン対応・引数検証）。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンのランク相関に基づく実装。
    - rank / factor_summary: ランク付け、ファクター統計要約（count/mean/std/min/max/median）。
  - research パッケージは data.stats の zscore_normalize を再エクスポート。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- OpenAI API キー（OPENAI_API_KEY）や各種トークン（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN など）は環境変数で扱う設計。
- 自動 .env ロード時に既存 OS 環境変数を保護する仕組み（protected set）を導入。

### 既知の制限・注意点 (Known issues / Notes)
- raw_financials からの PBR・配当利回り算出は現バージョンでは未実装（calc_value の注記あり）。
- DuckDB に依存するため、対象テーブル（prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar 等）が存在する前提の関数が多い。テストや初回起動時はスキーマ準備が必要。
- OpenAI 呼び出しは gpt-4o-mini と JSON mode を想定しているが、API 仕様変更に備えてエラーハンドリングとパースのフォールバックを実装している。
- テストのために OpenAI 呼び出し箇所（_call_openai_api）をモック・パッチすることを想定している（テスト容易性の配慮）。

---

今後の予定（例）
- ETL の具体的な pipeline 実装（差分計算・保存フローの高レベルラッパー）
- execution / strategy / monitoring の実装拡充（現状はパッケージ名の準備）
- AI レスポンスのより厳密な検証や追加のフェイルオーバー戦略

（以上）