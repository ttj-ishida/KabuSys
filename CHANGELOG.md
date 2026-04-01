# CHANGELOG

このプロジェクトは Keep a Changelog の形式に従って記録しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

すべての変更は semver に従います。

## [Unreleased]

- （なし）

## [0.1.0] - 2026-04-01

### 追加 (Added)
- パッケージ初期公開
  - 基本モジュール構成を追加: kabusys パッケージと以下のサブモジュールを実装
    - kabusys.config: 環境変数 / .env 読み込み・設定管理（自動ロード機能、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化）
    - kabusys.ai: ニュース NLP と市場レジーム判定
      - news_nlp.score_news: ニュース記事を OpenAI（gpt-4o-mini）でバッチ解析し、銘柄ごとのセンチメントを ai_scores テーブルへ書き込む。
        - JST ベースのニュース収集ウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST）
        - 1銘柄あたりの記事数・文字数制限、最大バッチサイズ制御、JSON Mode を利用した厳密なレスポンス検証
        - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフによるリトライ
        - レスポンスのバリデーションとスコアの ±1.0 クリップ
        - DuckDB の executemany 空リスト制約を考慮した冪等的な DELETE → INSERT ロジック
      - regime_detector.score_regime: ETF (1321) の 200 日移動平均乖離とマクロニュース（LLM）を合成して日次の市場レジーム（bull / neutral / bear）を判定し market_regime テーブルへ冪等書き込み
        - ma200_ratio 計算（ルックアヘッドバイアス回避のため target_date 未満のデータのみ使用）
        - マクロキーワードでニュースを抽出し LLM に投げる（記事がない場合は LLM 呼出しをスキップ）
        - OpenAI API の堅牢なリトライとフェイルセーフ（API 失敗時は macro_sentiment=0.0）
    - kabusys.research: ファクター計算・特徴探索ツール
      - factor_research.calc_momentum / calc_volatility / calc_value: DuckDB の prices_daily / raw_financials を用いたモメンタム・ボラティリティ・バリュー系ファクター算出
        - 200日 MA、ATR、出来高・売買代金指標、過去データ不足時の None 戻し等に対応
      - feature_exploration.calc_forward_returns / calc_ic / rank / factor_summary: 将来リターン計算、Spearman(IC) 計算、ランク変換、統計サマリー
        - 外部ライブラリに依存せず標準ライブラリと DuckDB を使用
    - kabusys.data: データプラットフォーム関連ユーティリティ
      - calendar_management: JPX カレンダーの管理と営業日ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）、夜間バッチ更新 job（calendar_update_job）
        - DB 登録値優先、未登録日は曜日ベースのフォールバック、最長探索日数制限、バックフィルと健全性チェック実装
      - pipeline / etl: ETL パイプライン基盤と ETLResult データクラス（差分更新、品質チェック、保存の冪等性を想定）
      - etl の公開インターフェース（ETLResult の再エクスポート）
    - その他: パッケージの __init__ による公開 API の整理（__all__）

- 環境変数読み込みの強化
  - .env / .env.local の自動読み込み（プロジェクトルート探索: .git または pyproject.toml による判定）
  - export KEY=val 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱いなどを正確にパース
  - .env と .env.local の優先度（OS 環境変数 > .env.local > .env）、override と protected（OS 環境変数保護）を実装
  - 必須設定取得時に未設定なら ValueError を送出する _require ユーティリティ
  - KABUSYS_ENV と LOG_LEVEL の値検証ロジックとユーティリティフラグ（is_live / is_paper / is_dev）

### 変更 (Changed)
- 設計方針の明文化（各モジュールに以下の方針を反映）
  - ルックアヘッドバイアス防止: datetime.today() / date.today() をスコープ内部で参照せず、外部から target_date を渡す設計
  - OpenAI 呼び出しや DB 書き込みはフェイルセーフにし、部分失敗が全体を壊さない設計（API 失敗時はスキップ or デフォルト値を使用）
  - DuckDB の互換性問題（executemany の空リスト不可等）に配慮した実装

### 修正 (Fixed)
- OpenAI API 呼び出し周りの堅牢化
  - retry/backoff ロジック（429・ネットワーク断・タイムアウト・5xx の扱い）を一貫実装し、最大リトライ回数超過時は警告ログを出して安全にフォールバックするようにした
  - JSON レスポンスのパース耐性を向上（JSON mode でも前後に余計なテキストが混ざるケースをハンドリング）
- DB 書き込みの冪等化とトランザクション制御を追加
  - market_regime / ai_scores への書き込みで BEGIN / DELETE / INSERT / COMMIT を用いた冪等保存を実装し、失敗時は ROLLBACK を試みる

### セキュリティ (Security)
- （このリリースにおける既知のセキュリティ修正はなし）

---

注記:
- 各 AI モジュールはデフォルトで環境変数 OPENAI_API_KEY を使うが、api_key を引数で注入できる設計のためテスト時にキーを差し替え可能です（テスト用に _call_openai_api を patch して挙動を置換可能）。
- DuckDB を用いた SQL 実装は互換性を考慮した実装になっていますが、実行環境の DuckDB バージョンによる細かな違いに注意してください。
- 本 CHANGELOG はソースコードの実装内容から推測して作成しています。