# CHANGELOG

すべての notable な変更はこのファイルに記録します。  
形式は「Keep a Changelog」に準拠しています（日本語）。  
バージョン番号は semver に従います。

## [Unreleased]

### 追加
- 開発初期のコードベースを追加（初期機能セット）。
  - 環境設定、AIベースのニュース解析・市場レジーム判定、データETL・カレンダー管理、リサーチ向け指標計算等を含む。

### 既知の制約
- OpenAI 呼び出しは gpt-4o-mini を想定した実装。API キーが必要。
- DuckDB を利用する前提。スキーマ（prices_daily, raw_news, market_calendar, raw_financials, ai_scores 等）が必要。
- 一部ファイルの末尾が未完（etl モジュールの最後に切れが確認される）ため、ビルド前にコード整合性の確認が必要。

---

## [0.1.0] - 2026-04-02

初回リリース。本リリースは以下の主要機能を実装します。

### 追加
- パッケージ基盤
  - kabusys パッケージの初期化（__version__ = 0.1.0、公開モジュールの __all__ を設定）。
- 設定管理（kabusys.config）
  - .env / .env.local 自動読み込み機能（プロジェクトルートは .git または pyproject.toml を基準に検索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用途）。
  - .env のパース機能を実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理等に対応）。
  - 環境変数保護（OS 環境変数を protected として上書きを制御）。
  - Settings クラスを提供（J-Quants / kabu API / Slack / DB パス / 監視設定 / システム設定などのプロパティを取得）。
  - KABUSYS_ENV / LOG_LEVEL の値検証（許容値チェック）と is_live / is_paper / is_dev のヘルパーを実装。
  - 必須環境変数未設定時に分かりやすいエラーメッセージを送出。

- AI モジュール（kabusys.ai）
  - news_nlp: ニュース記事を OpenAI（gpt-4o-mini）でスコアリングし ai_scores テーブルへ書き込む機能を実装。
    - 前日 15:00 JST 〜 当日 08:30 JST のニュースウィンドウを対象に集約・トリムしてバッチ送信。
    - バッチサイズ、記事数上限、文字数上限を設定（チャンク処理）。
    - JSON mode を想定したレスポンス検証（results 配列、code/score の検査、±1.0 でクリップ）。
    - 429 / ネットワーク断 / タイムアウト / 5xx を対象とした指数バックオフによるリトライ。
    - API 失敗時は該当チャンクをスキップして処理継続（フェイルセーフ設計）。
    - テスト容易性のため _call_openai_api を patch で差し替え可能。
  - regime_detector: ETF 1321 の 200 日移動平均乖離とマクロニュースの LLM センチメントを合成して日次の市場レジーム判定を実装。
    - ma200_ratio の計算（target_date 未満のデータのみ使用しルックアヘッドを防止）。
    - マクロニュースはキーワードフィルタ（日本・米国等）で抽出し LLM により -1.0〜1.0 を評価。
    - 合成ルール: 70% × MA 成分（スケール調整） + 30% × マクロセンチメント、スコアをクリップしてラベル付け（bull / neutral / bear）。
    - API 失敗時は macro_sentiment=0.0 として継続（フェイルセーフ）。
    - DB への書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実行。

- データモジュール（kabusys.data）
  - calendar_management: JPX カレンダー管理、営業日判定と関連ユーティリティを実装。
    - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を提供。
    - market_calendar が未取得の場合の曜日ベースフォールバック（週末は非営業日）を実装。
    - 夜間バッチ calendar_update_job を実装（J-Quants API から差分取得し冪等保存、バックフィル、健全性チェック）。
  - pipeline / etl:
    - ETLResult データクラスを公開（ETL の取得数・保存数・品質問題・エラーを集約）。
    - ETL パイプライン設計（差分更新、idempotent 保存、品質チェックの集約）に対応した基盤を実装。
    - jquants_client 経由での差分・保存処理を想定（関数名や処理フローの記載）。
  - etl モジュールは pipeline.ETLResult を再エクスポート。

- Research（kabusys.research）
  - factor_research: モメンタム / ボラティリティ / バリューなどのファクター計算を実装。
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（ma200_dev は200行未満で None）。
    - calc_volatility: atr_20 / atr_pct / avg_turnover / volume_ratio（データ不足時は None）。
    - calc_value: per（EPS が 0/欠損なら None）と roe を raw_financials と prices_daily から取得。
    - すべて DuckDB 上の SQL を利用して計算（価格・財務テーブルのみ参照、実取引 API へはアクセスしない）。
  - feature_exploration:
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - calc_ic: ファクターと将来リターン間のスピアマン（ランク）相関（IC）を計算。3 件未満で None を返す。
    - rank: 同順位は平均ランクにする実装（丸めで ties を検出）。
    - factor_summary: count/mean/std/min/max/median を標準ライブラリのみで計算。
  - research パッケージは zscore_normalize（kabusys.data.stats 由来）や上記関数群を再エクスポート。

### 変更
- なし（初回リリース）

### 修正
- なし（初回リリース）

### セキュリティ
- 環境変数の読み込みにおいて OS の既存環境変数をデフォルトで保護（.env が OS 環境変数を上書きしない）する設計を採用。

### 注意事項 / 実装上の設計判断
- ルックアヘッドバイアス防止: 全ての時刻関連ロジック（ニュースウィンドウ、MA 計算、ETL など）は内部で datetime.today() / date.today() を安易に参照しないよう配慮。target_date で明示的に制御する設計。
- OpenAI API 呼び出しは応答の不確実性を考慮し、JSON パース失敗や未知フィールドに対して安全にフォールバックする（例: レスポンスパース失敗時は該当処理をスキップして続行）。
- DuckDB のバージョン差異（executemany の空リスト扱い、配列バインドの互換性）を考慮した実装上の対応を行っている。
- テスト容易性: OpenAI 呼び出し部は差し替え可能（ユニットテストでモック可能）。

---

## 既知の問題 / TODO
- etl の最後が途中で切れている箇所があり、モジュール全体の完全性を要確認（コメントや未完成の関数が存在する可能性）。
- jquants_client 等の外部クライアント実装（fetch/save 関数）の存在を前提としているため、環境依存の実装/モックが必要。
- 実行前に DuckDB のスキーマ作成と必要テーブルの準備が必要。

---

作成・更新履歴
- 2026-04-02 - 0.1.0 初回リリース（本CHANGELOG 作成日）

（注）本 CHANGELOG は提供されたコードベースの内容から機能群・設計方針を推測して作成しています。実際のリリースノートは開発履歴・コミットメッセージに基づいて適宜調整してください。