# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
初回リリースを含む現時点での主要実装内容をコードベースから推測して日本語でまとめています。

## [Unreleased]

## [0.1.0] - 2026-04-03
初回リリース（推定）。日本株自動売買システム「KabuSys」のコア機能を実装。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期公開。バージョンは `0.1.0`。
  - __all__ により main サブパッケージ（data, strategy, execution, monitoring）を公開。

- 設定・環境変数管理（kabusys.config）
  - .env/.env.local 自動読み込み機構を実装（プロジェクトルートは .git または pyproject.toml を起点に探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト向け）。
  - .env パーサの強化：
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のエスケープ対応
    - インラインコメントの扱い（クォート有り無しで挙動を分離）
  - Settings クラスを提供し、各種設定値をプロパティで取得可能：
    - J-Quants / kabu ステーション / LINE API / DB パス (DuckDB/SQLite) / 監視関連パス・閾値 / 環境・ログレベル判定 など
  - 必須 env が未設定の場合は明示的に ValueError を発生させる _require を実装。
  - 有効な環境値とログレベルのバリデーション。

- AI モジュール（kabusys.ai）
  - news_nlp: ニュースを OpenAI（gpt-4o-mini）でセンチメント解析し ai_scores テーブルへ書き込む機能を実装。
    - タイムウィンドウ計算（JST 基準 → DB 比較は UTC naive datetime）
    - 銘柄ごとに記事を集約（記事数・文字数でトリム）
    - 最大 20 銘柄のバッチ処理、JSON mode を用いた API 呼び出し
    - API の 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ
    - レスポンスの厳密バリデーション（JSON 抽出、results の形式検証、未知コードの無視、スコアを ±1.0 にクリップ）
    - 部分成功に配慮した DB 更新（対象コードのみ DELETE→INSERT）およびトランザクション処理（BEGIN/COMMIT/ROLLBACK）
    - テスト容易性のため _call_openai_api を patch 可能に設計
  - regime_detector: マクロニュースと ETF（1321）の 200 日 MA 乖離を合成して日次の市場レジームを判定・保存する機能を実装。
    - ma200_ratio 計算（target_date より前のみを使用してルックアヘッド防止）
    - マクロキーワードで raw_news をフィルタしてタイトルを抽出
    - OpenAI 呼び出し（独自実装）で macro_sentiment を算出し、重み合成で regime_score を算出
    - API エラーはフェイルセーフで macro_sentiment=0.0 にフォールバック
    - レジーム（bull / neutral / bear）判定、market_regime テーブルへの冪等書き込み（DELETE→INSERT）
    - リトライ / エラー処理・ログ出力を実装

- データ層（kabusys.data）
  - calendar_management: JPX カレンダー管理と営業日判定ロジックを実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等を提供
    - market_calendar データの有無に応じた DB優先・未登録日の曜日フォールバックの一貫した挙動
    - calendar_update_job による J-Quants API からの差分取得・保存（バックフィル・健全性チェック含む）
  - pipeline / etl:
    - ETLResult データクラスを提供（ETL の取得数・保存数・品質チェック結果・エラー等を集約）
    - ETL パイプラインのためのユーティリティ（差分更新・バックフィル・品質チェック方針などの実装方針を反映）
  - ETLResult は kabusys.data.etl で再エクスポート

- Research（kabusys.research）
  - factor_research: ファクター計算モジュールを実装
    - calc_momentum: 1M/3M/6M リターン、ma200_dev（200日）等
    - calc_volatility: 20日 ATR, 相対ATR, 20日平均売買代金, 出来高比率 など
    - calc_value: PER / ROE（raw_financials の最新値を利用）
    - DuckDB 上で SQL とウィンドウ関数を用いて効率的に計算
  - feature_exploration: 解析ユーティリティを実装
    - calc_forward_returns: 任意ホライズンの将来リターン取得（複数ホライズンを1クエリで）
    - calc_ic: Spearman（ランク）による IC 計算（3 銘柄未満は None を返す）
    - factor_summary: count/mean/std/min/max/median を計算
    - rank: 同順位は平均ランクを返す安定実装（丸めで ties 抑制）
  - research パッケージは上記機能を再エクスポート

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 互換性のない変更 (Breaking Changes)
- （初回リリースのため該当なし）

### 廃止予定 (Deprecated)
- なし

### 削除 (Removed)
- なし

### セキュリティ (Security)
- OpenAI API キー取得に失敗した場合は ValueError を送出して明示的に通知（news_nlp / regime_detector）。
- .env 読み込みで OS 環境変数を保護する仕組み（protected set）を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。

### 注意点 / 既知の制約 (Known limitations)
- DuckDB executemany に空リストを渡せないバージョンに対するガードを実装している（空パラメータはスキップする）。
- API レスポンスのパース失敗や API 側の不安定さに対してはフォールバック（スコア 0.0／スキップ）する設計のため、外部 API 側の完全性に依存しないが、結果が欠落する可能性がある。
- 日付処理はすべて date / UTC-naive datetime を利用しており、timezone の混入に注意が必要。
- news_nlp / regime_detector は gpt-4o-mini（JSON mode）への依存があるため、OpenAI SDK 仕様変更やモデル仕様変更の影響を受ける可能性がある。
- strategy / execution / monitoring の実装はパッケージ公開名として存在しているが（__all__）、本リリースでの詳細実装は限定的である可能性がある（提示されたコードベースに依存）。

---

注: 本 CHANGELOG は与えられたコード内容と docstring から推測して作成しています。実際のコミット履歴やリリースノートが存在する場合はそちらを優先してください。