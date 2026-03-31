# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。  

なお本CHANGELOGは、提供されたコードベースの内容から機能・変更点を推測して作成しています。

現行バージョン: 0.1.0

Unreleased
----------
（なし）

[0.1.0] - 2026-03-31
-------------------
Added
- 基本パッケージ初期実装
  - パッケージメタ情報: kabusys.__version__ = "0.1.0"
  - 公開モジュール: data, strategy, execution, monitoring（__all__）

- 環境設定/ローダー（kabusys.config）
  - プロジェクトルートを .git または pyproject.toml から探索して .env, .env.local を自動読み込みする仕組みを実装
  - .env パーサーは export プレフィックス、引用符（シングル/ダブル）のエスケープ、インラインコメント処理をサポート
  - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - 環境変数保護（OS 環境変数を上書きしないための protected set）に対応
  - 必須値取得ヘルパー _require と Settings クラスを提供（J-Quants, kabu API, Slack, DB パス等のアクセス）
  - 許容値チェック: KABUSYS_ENV（development/paper_trading/live）、LOG_LEVEL（DEBUG/INFO/...）

- AI モジュール（kabusys.ai）
  - ニュースセンチメントスコアリング: score_news()
    - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini, JSON Mode）で銘柄ごとに -1.0〜1.0 のスコアを生成
    - バッチ処理（最大 20 銘柄/リクエスト）、記事トリム（最大記事数・最大文字数）を実装
    - レスポンスのバリデーションとクリッピング、部分成功時の DB 保護（対象コードのみ DELETE → INSERT）
    - レート制限・ネットワーク断・5xx での指数バックオフリトライ、失敗時は該当チャンクをスキップ
    - テスト容易性のため OpenAI 呼び出し部分は置換可能（_call_openai_api を patch できる）
  - 市場レジーム判定: score_regime()
    - ETF (コード 1321) の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を決定
    - マクロニュース抽出のキーワード群（日本／米国など）を定義、LLM 呼び出し失敗時はフェイルセーフで macro_sentiment = 0.0 を使用
    - レジーム結果を market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）
    - API リトライ・エラー処理・JSON パース保護を実装

- データプラットフォーム（kabusys.data）
  - カレンダー管理（calendar_management）
    - market_calendar を基にした営業日判定ユーティリティを実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）
    - DB 登録値優先、未登録日は曜日ベースでフォールバック（休日判定の一貫性を確保）
    - 夜間更新ジョブ calendar_update_job()：J-Quants API から差分取得→idempotent保存、バックフィルおよび健全性チェックを実装
  - ETL パイプライン（pipeline）
    - ETLResult データクラスを公開（取得件数・保存件数・品質チェック結果・エラーの集約）
    - 差分取得、バックフィル、品質チェック、idempotent 保存の設計に基づくユーティリティ

- 研究用ユーティリティ（kabusys.research）
  - ファクター計算（factor_research）
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算
    - calc_value: raw_financials から最新の EPS/ROE を取得して PER/ROE を計算
    - DuckDB を用いた SQL ベース実装。結果は (date, code) キーの辞書リストで返却
  - 特徴量探索（feature_exploration）
    - calc_forward_returns: 指定ホライズンに対する将来リターン（デフォルト [1,5,21]）を計算
    - calc_ic: スピアマンランク相関（情報係数）を実装（3 銘柄未満で None を返す）
    - rank: 同順位は平均ランクで扱うランク化ユーティリティ
    - factor_summary: count/mean/std/min/max/median の統計サマリーを計算
  - zscore_normalize は data.stats から再エクスポート

Changed
- 初回リリースのため特になし（新規追加中心）

Fixed
- 初回リリースのため特になし

Notes / 実装上の重要な設計判断
- ルックアヘッドバイアス対策
  - 各 AI / 研究関数は datetime.today()/date.today() を内部参照せず、必ず target_date 引数を明示的に受け取る設計
  - DB クエリは target_date 未満・以前等の排他条件で将来データを参照しないよう注意している
- OpenAI 呼び出し
  - gpt-4o-mini を利用（JSON Mode で厳密な JSON を期待）
  - レートリミット・ネットワーク障害・5xx に対するリトライ・バックオフを統一的に実装
  - テスト容易性のため API 呼び出しポイントを patch 可能にしている
- DB 書き込みの冪等性
  - market_regime / ai_scores 等は既存行を削除してから挿入することで冪等性を担保（部分失敗時の既存データ保護を考慮）
  - DuckDB の executemany の挙動（空リスト不可など）に配慮したガード実装
- フォールバック
  - カレンダー未取得時は曜日ベース（単純に土日除外）で営業日判定を行う
  - AI 呼び出し失敗時はスコアを 0.0（中立）にフォールバックして処理継続
- 環境変数
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（Settings により参照）
  - OpenAI API キーは各関数の api_key 引数または環境変数 OPENAI_API_KEY で解決

Known limitations / TODO（コードから推測）
- PBR・配当利回り等の一部バリューファクターは未実装（calc_value の注記参照）
- strategy / execution / monitoring モジュールの詳細は本差分からは確認できないため、別実装が必要
- テストカバレッジや CI 設定、実稼働用のエラーレポーティング（Slack 通知等）の統合は今後の拡張想定

ライセンス
- コード内にライセンス明示なし（プロジェクトの実際のライセンスは別途確認してください）

以上。必要であれば各モジュールごとの詳細な変更点（関数単位の説明や公開 API の使用例）を追記します。