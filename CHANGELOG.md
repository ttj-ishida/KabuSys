# Changelog

すべての変更は Keep a Changelog の形式に従います。初回公開バージョンは 0.1.0 です。

## [Unreleased]

(なし)

## [0.1.0] - 2026-03-29

### 追加
- 基本パッケージ情報
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として定義。
  - パッケージ外部公開モジュールを `__all__` で宣言（data, strategy, execution, monitoring）。

- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を自動読み込みするユーティリティを追加。
    - 自動読み込み順序: OS 環境変数 > .env.local > .env。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動ロードを無効化可能。
    - プロジェクトルート検出は `.git` または `pyproject.toml` を起点に実装（CWD に依存しない）。
  - .env パーサーの実装:
    - コメント・空行を無視、`export KEY=val` 形式をサポート。
    - シングル/ダブルクォート内のエスケープ処理、インラインコメント処理を実装。
  - 環境変数読み込み時の保護機構:
    - OS 環境変数を protected として .env で上書きされないよう保持。
  - 必須環境変数取得ヘルパー `_require` と Settings クラスを提供。
    - J-Quants / kabu API / Slack / DB パス等のプロパティを定義。
    - `KABUSYS_ENV` / `LOG_LEVEL` の値検証を実装（不正な値は ValueError を送出）。
    - パス設定は `Path.expanduser()` を用いて解決。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols から銘柄別に記事を集約し、OpenAI（gpt-4o-mini）でセンチメントを算出して `ai_scores` テーブルへ書き込む。
    - 処理の特徴:
      - スコアリング対象ウィンドウは JST 基準で「前日 15:00 〜 当日 08:30」を採用（UTC に変換して DB 検索）。
      - 1 銘柄あたり最大記事数と最大文字数でトリム（トークン肥大化対策）。
      - 最大 20 銘柄ずつのバッチ送信（_BATCH_SIZE）。
      - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフによるリトライ。
      - JSON mode 用のレスポンス検証 / 復元ロジック（前後余計なテキストが混ざる場合の {} 抽出）。
      - スコアは ±1.0 にクリップ。レスポンス検証失敗時は当該チャンクをスキップ（例外は伝播させない）。
      - DuckDB 互換性のため、空パラメータを executemany に渡さないようガードしてから DELETE/INSERT を実行。
    - 公開 API: score_news(conn, target_date, api_key=None) → 書き込んだ銘柄数を返す。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して市場レジーム（bull / neutral / bear）を判定。
    - 処理の特徴:
      - ma200_ratio は target_date 未満のデータのみを使用（ルックアヘッド防止）。
      - マクロ記事は predefined マクロキーワードでフィルタ、最大件数制限あり。
      - OpenAI 呼び出しは専用ラッパーで行いリトライ（429, 接続エラー, タイムアウト, 5xx を考慮）。
      - API 失敗時は macro_sentiment = 0.0（フェイルセーフ）として処理継続。
      - レジームスコアを合成して `market_regime` テーブルへ冪等（BEGIN / DELETE / INSERT / COMMIT）で書き込み。
    - 公開 API: score_regime(conn, target_date, api_key=None) → 成功時 1 を返す。

- Data モジュール（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダー用の夜間更新ジョブ `calendar_update_job` を実装（J-Quants API 経由）。
    - 営業日判定ユーティリティを提供:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days。
    - 設計上の特徴:
      - DB 登録データが存在する場合は DB を優先、未登録日は曜日ベースでフォールバック（週末を除く）。
      - 最大探索日数の上限を設け無限ループ防止。
      - バックフィル（直近数日分を再フェッチ）と健全性チェック（将来日付が異常に遠い場合はスキップ）。
  - ETL パイプライン（kabusys.data.pipeline, kabusys.data.etl）
    - ETL の結果を表すデータクラス `ETLResult` を公開（kabusys.data.ETLResult として再エクスポート）。
    - パイプラインのユーティリティ:
      - 差分取得のためのテーブル最終日取得、テーブル存在チェック、日付調整等を実装（DuckDB を利用）。
    - 設計方針:
      - 差分更新（営業日単位）、バックフィル、保存は idempotent（ON CONFLICT DO UPDATE 想定）。
      - 品質チェックモジュールと連携して品質問題を収集するが、致命的エラーがあってもパイプラインは可能な限り続行し、呼び出し元が判断できるようにする。

- Research モジュール（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum / Value / Volatility（流動性含む）を計算する関数を実装:
      - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（不足時は None を返す）。
      - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率。
      - calc_value: raw_financials から EPS/ROE を取得し PER/ROE を計算。
    - 全て DuckDB 内の prices_daily / raw_financials のみ参照し、外部発注等は行わない。
  - 特徴量探索（kabusys.research.feature_exploration）
    - calc_forward_returns: target_date から指定ホライズン（デフォルト 1,5,21 営業日）先までのリターンを一度のクエリで取得。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を実装（有効レコードが 3 件未満なら None）。
    - rank: 平均ランク（同順位は平均ランク）を算出するユーティリティ（丸め処理で ties の安定化）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。

### 変更
- 設計上の共通方針・制約を明確化（モジュールごとに共通）
  - ルックアヘッドバイアス防止のため、datetime.today()/date.today() を直接参照しない実装を採用している箇所があることをドキュメントに明記。
  - DuckDB を一貫して利用し、NULL やデータ不足時の挙動（None を返す、または中立値を使用する）を明確に実装。
  - OpenAI 呼び出しは JSON mode を利用し、レスポンスパース処理を厳格化（例外時はフェイルセーフにフォールバック）。

### 修正
- エラー処理の強化
  - OpenAI 呼び出しに対して 5xx/ネットワーク系のリトライ処理を追加し、全リトライ消費時にログを残して安全にフォールバックするようにした。
  - DB 書き込み時に冪等性を意識したトランザクション（BEGIN / DELETE / INSERT / COMMIT）とロールバック処理を導入。ロールバック失敗時は警告ログを出力。

### 既知の制限 / 注意事項
- OpenAI の API キーは関数引数か環境変数 `OPENAI_API_KEY` によって解決される。未設定時は ValueError を送出する箇所があるため実行前に設定が必要。
- news_nlp / regime_detector は gpt-4o-mini（JSON Mode）へ依存しており、モデル応答フォーマットの違いによりパースが失敗する可能性がある。失敗したチャンクはスキップされる設計。
- 一部モジュールは外部クライアント（jquants_client 等）に依存するため、実行前に適切な API クライアントの組み込みが必要。
- ファイルの一部（例: data.pipeline の _adjust_to_trading_day の続きを含む箇所）は現在のスナップショットで途中まで実装されている（今後の拡張を予定）。

---

この CHANGELOG はコードベースの現在の状態から推測して作成しています。実際のリリースノート作成時はコミット履歴や変更差分と照合してください。