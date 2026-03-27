# CHANGELOG

すべての変更は Keep a Changelog 準拠で記載しています。  
このファイルはコードベースの内容から推測して作成した初期リリース向けの変更履歴です。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-27
初期リリース。日本株自動売買システム "KabuSys" のコア機能群を実装。

### 追加 (Added)
- パッケージ基盤
  - パッケージのエントリポイントを追加（kabusys.__init__）。公開モジュール: data, strategy, execution, monitoring。
  - バージョン情報: `__version__ = "0.1.0"`。

- 設定/環境管理
  - .env ファイルまたは環境変数から設定を読み込む `kabusys.config` を実装。
  - プロジェクトルート自動検出ロジック（.git または pyproject.toml を基準）を導入し、CWD に依存しない自動 .env ロードを実現。
  - .env のパース機能を強化（export prefix 対応、シングル/ダブルクォート内のエスケープ処理、行中コメントの扱いなど）。
  - 自動ロードの上書きルール:
    - OS 環境変数優先
    - `.env.local` は `.env` の上書きとして読み込む
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動ロードを無効化可能
  - 必須環境変数取得ヘルパー `_require` と、Settings クラスを提供。主要な設定プロパティ:
    - J-Quants / kabuステーション / Slack / DB パス / 環境（development/paper_trading/live）/ログレベル 等

- AI（自然言語処理）モジュール
  - ニュースセンチメント解析: `kabusys.ai.news_nlp.score_news`
    - 前日15:00 JST ～ 当日08:30 JST のニュースウィンドウを計算する `calc_news_window`
    - ニュースを銘柄ごとに集約し、OpenAI（gpt-4o-mini）へバッチ送信してスコアを算出
    - バッチサイズ、記事数・文字数トリム、JSON モードのレスポンス検証、スコアクリップ（±1.0）を実装
    - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライを実装
    - DuckDB へ冪等的に書き込む処理（部分失敗時に既存データを保護）
  - 市場レジーム判定: `kabusys.ai.regime_detector.score_regime`
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次レジーム判定（bull/neutral/bear）を行う
    - OpenAI 呼び出しのフェイルセーフ（API失敗時は macro_sentiment=0.0）
    - API 呼び出し/リトライロジックと結果の JSON パースおよびクリップ処理を実装
    - `market_regime` テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）

- データ関連モジュール
  - ETL パイプライン: `kabusys.data.pipeline` と `ETLResult` データクラスを実装
    - 差分取得、保存（jquants_client 経由で冪等保存）、品質チェック統合を想定
    - ETL 実行結果の監査向け辞書変換機能を提供
  - ETL 公開インターフェースの再エクスポート: `kabusys.data.etl.ETLResult`
  - マーケットカレンダー管理: `kabusys.data.calendar_management`
    - JPX カレンダー夜間更新ジョブ（`calendar_update_job`）を実装。バックフィルと健全性チェックを含む
    - 営業日判定ユーティリティ: `is_trading_day`, `next_trading_day`, `prev_trading_day`, `get_trading_days`, `is_sq_day`
    - カレンダーデータがない場合の曜日ベースのフォールバック実装
    - DuckDB でのテーブル存在チェックや日付変換ユーティリティを提供

- リサーチ / ファクター計算
  - `kabusys.research` パッケージを導入。提供関数:
    - ファクター計算: `calc_momentum`, `calc_value`, `calc_volatility`
      - Momentum: 1M/3M/6M リターン、200 日 MA 乖離
      - Value: PER、ROE（raw_financials から最新財務を取得）
      - Volatility: 20 日 ATR、相対 ATR、平均売買代金、出来高比など
    - 特徴量探索: `calc_forward_returns`, `calc_ic`, `factor_summary`, `rank`
      - 将来リターン計算（任意ホライズン、入力検証あり）
      - Spearman ランク相関（IC）計算、統計サマリー、ランク化ユーティリティ
  - 設計方針をコードレベルで明記（DuckDB のみ参照、ルックアヘッドバイアス防止、外部 API への非依存など）

### 変更 (Changed)
- なし（初期リリース）

### 修正 (Fixed)
- .env 読み込み時のエッジケース対策を多く含む（クォート内のエスケープ、インラインコメント判定、export プレフィックス処理など）。

### セキュリティ (Security)
- なし（初期リリース）。ただし、環境変数で API キーを扱う設計のため、運用時はシークレット管理に注意。

### 既知の注意点 / 制約事項
- DuckDB のバージョン依存:
  - 一部処理で executemany に空リストを渡すとエラーになるため、空チェックを行っている（DuckDB 0.10 を想定した互換性対策）。
- OpenAI SDK 及び API:
  - gpt-4o-mini を想定した JSON Mode を使用。API 呼び出し失敗時はフェイルセーフ（スコア 0.0）で継続する設計。
  - API キーは引数で注入可能（テスト容易化）または環境変数 OPENAI_API_KEY を利用。
- ルックアヘッドバイアス回避:
  - 日付決定は内部で datetime.today()/date.today() に依存しない方針（target_date を明示的に渡す設計）。
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等が設定されていることを前提とする API がある（Settings のプロパティ参照）。
- 部分失敗時の DB 保護:
  - ai_scores や market_regime への書き込みは、対象コードを絞って置換（DELETE → INSERT）することで部分失敗時に既存データを保護するよう設計。

---

作成者注: この CHANGELOG は提示されたコードの実装内容から推測して作成したもので、実際のリリースノートと異なる可能性があります。運用上の正確な変更履歴やリリース日、Breaking Changes の扱いはプロジェクトのリリースポリシーに従って更新してください。