# Keep a Changelog 変更履歴

すべての変更は慣例に従いカテゴリ別に記載します。日付はリリース日です。

## [Unreleased]

## [0.1.0] - 2026-03-31
最初の公開リリース。日本株自動売買システム「KabuSys」のコアライブラリ群を実装しました。主な追加点は以下のとおりです。

### 追加 (Added)
- パッケージ初期化
  - パッケージルート: `kabusys`（__version__ = 0.1.0）。
  - パッケージ公開モジュール: data, strategy, execution, monitoring を __all__ に設定。

- 環境設定 / 設定管理 (`kabusys.config`)
  - .env ファイル（.env, .env.local）および環境変数からの自動読み込み機能を実装。
    - プロジェクトルート検出: `.git` または `pyproject.toml` を親ディレクトリから探索して特定。
    - 自動読み込みは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により無効化可能。
    - OS 環境変数を保護するための上書き制御（`.env.local` は上書き、`.env` は未設定時のみ適用）。
  - .env パーサ実装:
    - コメント行・export 形式サポート、クォート内のエスケープ処理、インラインコメントルールなどに対応。
  - Settings クラスを提供し、主要設定値をプロパティ経由で取得:
    - J-Quants / kabuステーション / Slack トークン等の必須キー取得（未設定時は ValueError）。
    - DB パス（DuckDB/SQLite）、監視用しきい値（CPU/Memory/Disk）、PID ファイルパス等の既定値。
    - 実行環境（development / paper_trading / live）とログレベルの検証・判定ユーティリティ（is_live 等）。

- AI ニュース/レジーム判定 (`kabusys.ai`)
  - ニュースセンチメント（銘柄ごと）スコアリング: `score_news`（kabusys.ai.news_nlp）
    - タイムウィンドウ設定（前日 15:00 JST 〜 当日 08:30 JST を UTC に変換して使用）。
    - raw_news と news_symbols を集約し、1銘柄あたり最大記事数／文字数でトリム。
    - OpenAI（デフォルト model: gpt-4o-mini）へバッチ送信（最大 20 銘柄/回）。
    - JSON Mode を期待し、レスポンスのバリデーションとスコア ±1.0 のクリップ処理を実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx は指数バックオフでリトライ。致命的でない失敗はスキップして継続（フェイルセーフ）。
    - 成功した銘柄のみ ai_scores テーブルへ置換的に書き込み（DELETE → INSERT、部分失敗でも既存データ保護）。
    - テスト用に API 呼び出し箇所を差し替え可能（モック化しやすい設計）。
  - 市場レジーム判定: `score_regime`（kabusys.ai.regime_detector）
    - ETF 1321（Nikkei 225 連動）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次でレジーム判定（'bull'/'neutral'/'bear'）。
    - MA 計算は target_date 未満のデータのみ使用しルックアヘッドバイアスを防止。
    - マクロキーワードで raw_news をフィルタし、最大件数で LLM 評価。API エラー時は macro_sentiment=0.0 にフォールバック。
    - OpenAI 呼び出しは専用実装で、リトライ／エラー判定ロジックを持つ。
    - 計算結果は market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。

- データプラットフォーム / ETL / カレンダー (`kabusys.data`)
  - マーケットカレンダー管理 (`calendar_management`)
    - market_calendar テーブルを利用した営業日判定ロジックを実装:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day などを提供。
      - DB 登録値を優先し、未登録日は曜日ベースでフォールバック（週末を非営業日扱い）。
      - 最大探索日数の上限を設定し無限ループを防止。
    - 夜間バッチ更新ジョブ `calendar_update_job`:
      - J-Quants API から差分取得し market_calendar を冪等保存（バックフィル、健全性チェックあり）。
  - ETL パイプライン (`pipeline`)
    - ETLResult データクラスを公開（kabusys.data.etl を通じて再エクスポート）。
      - ETL の取得数 / 保存数、品質チェック結果、エラー一覧などを保持。 has_errors / has_quality_errors / to_dict 等のユーティリティを提供。
    - 差分更新、保存（jquants_client の save_* を想定）、品質チェックの流れを想定した設計（差分取得、backfill、品質問題の収集・報告）。
    - 内部ユーティリティ: テーブル存在チェック、最大日付取得など（DuckDB 前提）。

- リサーチ / ファクター計算 (`kabusys.research`)
  - ファクター計算群 (`factor_research`)
    - calc_momentum: mom_1m/mom_3m/mom_6m、200 日 MA 乖離（ma200_dev）を DuckDB SQL で計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率等を計算。
    - calc_value: raw_financials から最新財務データを取得し PER / ROE を計算（EPS が無効な場合は None）。
    - 設計方針: DuckDB に対する SQL ベースの実装で、外部 API や発注機能に依存しない。
  - 特徴量探索 / 統計 (`feature_exploration`)
    - calc_forward_returns: 指定日から将来ホライズン（1,5,21 日など）までのリターンを計算（存在しない場合は None）。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。有効レコードが 3 未満だと None。
    - rank: 同順位は平均ランクとするランク関数（丸め処理により ties 検出を安定化）。
    - factor_summary: 指定カラムの count/mean/std/min/max/median を計算する集計関数。
    - すべて標準ライブラリと DuckDB のみで実装（pandas 等に依存しない）。

### 変更 (Changed)
- この初期リリースでは互換性問題を生じさせる過去バージョンからの変更はありません（新規公開）。

### 修正 (Fixed)
- 初版のため既知のバグ修正履歴はありません。

### 注意事項 / 設計上のポイント
- ルックアヘッドバイアス対策:
  - すべての日時判定やデータ取得処理は内部で date.today()/datetime.today() を直接参照しない設計（呼び出し側が target_date を渡す方式）。
- OpenAI API 利用に関する挙動:
  - デフォルトモデルは gpt-4o-mini。JSON Mode を利用し、レスポンスの厳密な JSON パースとバリデーションを行う。
  - API エラー時は非破壊的にフォールバック（0.0 等）して処理を継続する方針。
- DuckDB に対する実装:
  - executemany に空リストを渡すと問題になるバージョンへの対応など、DuckDB の互換性に配慮した実装がなされている。
- テスト容易性:
  - OpenAI 呼び出し箇所や内部関数はモック差替えを想定して実装（unittest.mock.patch 等で差し替え可能）。

---

今後のリリースでは以下のような改善が想定されます:
- strategy / execution / monitoring モジュールの具現化（発注ロジック・実行監視）。
- より詳細な品質チェックルールの追加とアラート連携（Slack 等）。
- 単体テスト／統合テスト・CI 設定の追加。
- OpenAI パラメータやモデル選択の柔軟化。

必要であれば、各機能（AI スコアリング、ETL、カレンダー、ファクター計算）の詳細な使い方や API 例を CHANGELOG に追記せずに別ドキュメントとして用意できます。どの領域の追記が必要か教えてください。