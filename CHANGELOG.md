# CHANGELOG

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」準拠です。  

- 英語版の見出しを日本語化していますが、慣例に従ってセクション構成はそのまま使用します。
- 日付はコードベースの最終更新時点に合わせています（2026-04-04）。

## [Unreleased]

## [0.1.0] - 2026-04-04

初期リリース。日本株自動売買システム「KabuSys」の基盤機能を実装しました。主な追加内容は以下のとおりです。

### 追加
- 基本パッケージの公開
  - パッケージ名: kabusys
  - __version__ = 0.1.0
  - __all__ に data, strategy, execution, monitoring を定義（将来の機能拡張を想定）

- 環境設定 / 設定管理（kabusys.config）
  - .env ファイルおよび OS 環境変数の読み込み機能を実装（プロジェクトルートは .git / pyproject.toml を探索して自動検出）
  - .env パーサーは以下に対応：
    - コメント行、export KEY=val 形式、シングル／ダブルクォート内のエスケープ、インラインコメントの認識（クォート有り／無しで差異あり）
  - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト用途などを考慮）
  - 既存 OS 環境変数は保護され、.env.local は .env を上書きする優先順位
  - Settings クラスを提供（環境変数から各種設定値を取得）
    - J-Quants / kabu API / LINE / データベースパス / 監視設定 / システム設定（env, log_level 等）
    - 必須設定が未設定の場合は ValueError を送出する保護機構

- AI 関連（kabusys.ai）
  - news_nlp（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini）のJSON Modeを用いて銘柄別センチメントを算出
    - バッチ処理（最大20銘柄/チャンク）、トークン肥大化対策（記事数・文字数制限）を実装
    - リトライ（429・ネットワーク断・タイムアウト・5xx）を指数バックオフで実施
    - レスポンスの厳格なバリデーション（JSON抽出、results配列、code/score検証）とスコアの ±1.0 クリップ
    - ai_scores テーブルへの冪等的な書き換え（該当コードのみ DELETE → INSERT）
    - テスト容易性: OpenAI 呼び出しを置き換え可能（_call_openai_api の patch を想定）
    - タイムウィンドウ計算ユーティリティ calc_news_window を提供（JST基準）

  - regime_detector（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動）の200日移動平均乖離（重み70%）とマクロ系ニュースのLLMセンチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定
    - raw_news からマクロキーワードでフィルタして LLM へ投げるフローを実装
    - OpenAI呼び出しは独立実装。API障害時は macro_sentiment=0.0 としてフォールバック
    - market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）
    - ルックアヘッドバイアス防止の設計（date < target_date 等）

- データプラットフォーム（kabusys.data）
  - calendar_management
    - JPX カレンダー管理と営業日ロジックを実装：
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - market_calendar 未取得時は曜日ベースのフォールバック（週末を休場扱い）
    - calendar_update_job: J-Quants API から差分取得 → 冪等保存。バックフィルと健全性チェックを実装
  - pipeline / ETL
    - ETLResult データクラスを実装（取得件数・保存件数・品質問題・エラーを集約）
    - ETL フロー設計に沿った差分取得、保存、品質チェックのための基礎コード
    - jquants_client との連携想定（fetch / save 関数呼び出し）

- リサーチ / ファクター群（kabusys.research）
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、200日MA乖離の算出（DuckDB SQL + ウィンドウ関数）
    - calc_volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比率
    - calc_value: PER（EPS が 0 / 欠損時は None）、ROE（raw_financials から取得）
    - データ不足時は None を返す挙動で安全化
  - feature_exploration
    - calc_forward_returns: 指定ホライズンの将来リターンを一括取得（LEAD を使用）
    - calc_ic: スピアマンランク相関（ランクは同順位平均ランクを採用）
    - rank, factor_summary: ランク計算・統計サマリー（count/mean/std/min/max/median）
  - いずれも外部依存を使わず DuckDB + 標準ライブラリで実装

### 性能・堅牢性・テスト設計
- ルックアヘッドバイアス回避を各所で設計方針に明記（datetime.today()/date.today() の直接参照回避）
- API 呼び出し箇所はリトライ（指数バックオフ）、5xx と非5xx を分離して処理
- OpenAI API 呼び出し（news_nlp / regime_detector）はユニットテストで差し替え可能（patch を想定）
- DuckDB の executemany の制約（空リスト不可）に対応したガード実装
- DB 書き込みは可能な限り冪等（DELETE → INSERT など）で実装

### セキュリティ・運用
- 必須の環境変数を明示（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY 等）
- .env の自動ロードで OS 環境変数を上書きしない保護機構を実装（protected set）
- プロセス監視用設定（PID ファイル、KILL フラグ、CPU/MEM/DISK 閾値）を Settings に含む

### 既知の制限 / 注意点
- 一部機能は外部テーブル（prices_daily, raw_news, news_symbols, raw_financials, market_regime, ai_scores, market_calendar 等）の存在を前提としており、テーブル未作成時の挙動は一部で None / 0 を返すか例外が発生する場合があります。
- score_news / score_regime は OpenAI API キーが未設定だと ValueError を発生させます（明示的なエラー）。
- calc_value は現バージョンで PBR・配当利回りを未実装（注記あり）。
- data.__init__ は空で、jquants_client / quality モジュール等は外部実装が必要（このコードベース内での実装は限定的）。
- 一部の関数（例: pipeline._get_max_date の続き実装）がファイルの途中で切れている可能性があり、ETL の完全な実装は追加作業が必要です。

---

参照:
- バージョンはパッケージルートの __version__（0.1.0）に依存しています。今後のリリースでは「Added / Changed / Fixed / Security / Removed」の各セクションを運用方針に従って更新してください。