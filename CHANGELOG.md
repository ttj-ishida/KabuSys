# CHANGELOG

本ドキュメントは Keep a Changelog の形式に準拠します。  
コードベース（kabusys パッケージ）の変更点・初期リリースの内容を、ソースコードから推測して日本語でまとめています。

すべての変更はソースコードの現状に基づく推測です。実際のコミット履歴がある場合はそちらを優先してください。

## [Unreleased]
- 次期リリース向けの未確定変更はここに記載します。

## [0.1.0] - 2026-04-01
初回リリース（推定）。以下の主要機能を含みます。

### 追加（Added）
- パッケージのエントリポイントとバージョン
  - `kabusys.__version__ = "0.1.0"`
  - 公開モジュール: data, strategy, execution, monitoring（`__all__`）

- 環境設定/読み込み（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む自動ローダー（プロジェクトルートを .git または pyproject.toml から探索）
  - .env のパース機能（`export KEY=val`、クォートとバックスラッシュエスケープ、コメント処理を考慮）
  - `.env` / `.env.local` の読み込み優先度（OS 環境変数保護、override 制御）
  - 自動ロードを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD`
  - 必須環境変数取得のための `_require` と `Settings` クラスを提供
    - J-Quants / kabu ステーション / Slack / DB パス / 監視閾値 / ログレベル / 実行環境（development/paper_trading/live）などの設定プロパティ
    - `KABUSYS_ENV` と `LOG_LEVEL` のバリデーション
    - 便利プロパティ: `is_live`, `is_paper`, `is_dev`

- AI 関連（src/kabusys/ai）
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を元に銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini, JSON mode）へバッチ送信してセンチメントを算出
    - タイムウィンドウの計算（JST ベース → UTC naive datetime: 前日 15:00 JST 〜 当日 08:30 JST）
    - バッチ処理（1 API コールあたり最大 20 銘柄）、1 銘柄あたりの記事・文字数のトリム (_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK)
    - 再試行（429/ネットワーク/タイムアウト/5xx に対する指数バックオフ）、レスポンスの厳密なバリデーション
    - スコアは ±1.0 にクリップ、取得済み銘柄のみ ai_scores テーブルへ置換（DELETE → INSERT）して部分失敗に耐性
    - テスト容易性のため OpenAI 呼び出し関数を差し替え可能（モジュール内 private 実装）

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して日次でレジーム判定（'bull' / 'neutral' / 'bear'）
    - ma200_ratio の計算（target_date 未満のみ利用、データ不足時は中立 1.0 を使用）
    - マクロ記事抽出（タイトルベースでマクロキーワードをマッチ）
    - OpenAI 呼び出し（gpt-4o-mini、JSON 出力期待）でマクロセンチメントをスコア化。API 失敗時は 0.0 をフォールバック
    - レジームスコア合成および閾値判定（BULL/B EAR 閾値）と idempotent な DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）
    - API 呼び出しの失敗に対する再試行ロジックとログ出力

- リサーチ/ファクター計算（src/kabusys/research）
  - factor_research モジュール
    - calc_momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200日MA乖離）の計算（prices_daily テーブルのみを参照）
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率の計算
    - calc_value: PER（EPS が有効な場合）、ROE（raw_financials から最終レコードを取得）
    - 設計上、DB（DuckDB）内の SQL ウィンドウ関数を活用し、外部 API へはアクセスしない

  - feature_exploration モジュール
    - calc_forward_returns: 将来リターン（指定ホライズンの終値に基づく）を一度のクエリで取得（デフォルト [1,5,21]）
    - calc_ic: スピアマン順位相関（Information Coefficient）計算。3 銘柄未満で None を返す。
    - rank: 同順位の平均ランク、丸めを行って ties の検出誤差を低減
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を算出
  - research パッケージは zscore_normalize（kabusys.data.stats）を再エクスポート

- データ基盤（src/kabusys/data）
  - calendar_management モジュール
    - JPX 市場カレンダー管理：is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - market_calendar テーブルが存在する場合は DB 値を優先、未登録日は曜日ベースのフォールバック（weekend を休日として扱う）
    - calendar_update_job: J-Quants API から差分取得・バックフィル（直近数日再フェッチ）・健全性チェックを行い market_calendar を更新
    - 探索上限（_MAX_SEARCH_DAYS=60）やバックフィル・先読み日数の定義

  - ETL およびパイプライン（src/kabusys/data/pipeline.py, etl.py）
    - ETLResult データクラスを定義（取得件数・保存件数・品質チェック結果・エラー一覧など）
    - pipeline モジュールの型（ETLResult）を data.etl で再エクスポート
    - パイプライン設計: 差分更新、idempotent な保存（jquants_client の save_* を利用）、品質チェックを集約（重大度に応じた判定を保持）

### 変更（Changed）
- （初回リリースのため該当なし）

### 修正（Fixed）
- （初回リリースのため該当なし）

### セキュリティ（Security）
- OpenAI API キーは引数注入も可能（関数引数優先、未指定時は環境変数 OPENAI_API_KEY を参照）。キーの取り扱いはコード側で直接ログ出力しない設計。

### 設計上のポイント（ドキュメントに明示）
- ルックアヘッドバイアス対策:
  - target_date の計算で datetime.today()/date.today() を参照しない設計（テスト／再現性重視）
  - DB クエリでは date < target_date / date BETWEEN ... といった排他条件で将来データ利用を回避
- フェイルセーフ:
  - 外部 API（OpenAI / J-Quants）失敗時は例外を全体に伝播させず、フェイルセーフ値（例: macro_sentiment=0.0、スキップ）で継続できるようログ出力して処理を続行
- テスト容易性:
  - OpenAI 呼び出しをモジュール内でラップしており、テスト時に差し替え可能（unittest.mock.patch）
- DuckDB 互換性への配慮:
  - executemany に空リストを渡さないチェックなど、DuckDB バージョン差異に対応するコード

### 既知の問題 / 注意点（Known issues / Notes）
- src/kabusys/data/pipeline.py の末尾近辺に不完全な実装・タイポの痕跡が見られます（`return date.fro` のような不完全な戻り値）。この部分は実装が途中で切れている可能性が高く、修正が必要です。
- 一部のモジュール（例: src/kabusys/data/__init__.py）は空のままになっており、パッケージの公開 API を整理する余地があります。
- OpenAI SDK のエラーハンドリングは将来の SDK 変更を想定しているものの、実行環境の SDK バージョン差異に注意が必要です。
- 実稼働環境での発注・実装（strategy / execution / monitoring パッケージの内容）は本リリースでは確認できる範囲に依存します。実際の発注ロジックは本 CHANGELOG の範囲外（別途レビュー推奨）。

---

この CHANGELOG はソースコードから推測して作成しています。実際の変更履歴（Git コミット）やリリースノートが存在する場合はそちらを優先してください。必要であれば、各モジュールごとにより詳細な変更点（関数別・パラメータ別の例）を追記します。