CHANGELOG
=========

すべての重要な変更点をこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

Unreleased
----------

（なし）

0.1.0 - 2026-03-27
------------------

Added
- パッケージ初版リリース (kabusys v0.1.0)
  - パッケージ情報:
    - src/kabusys/__init__.py にて __version__ = "0.1.0" を設定。
    - パッケージ公開インターフェースとして data, strategy, execution, monitoring をエクスポート。

- 環境設定/ロード機能（src/kabusys/config.py）を追加
  - .env/.env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を探索して特定）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env 行パーサを実装:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応。
    - コメントの扱い（クォート外で '#' の前が空白/タブの場合はコメント扱い）に対応。
  - .env ファイル読み込みは既存 OS 環境変数を保護する機構（protected set）を備え、override フラグにより上書き動作を制御。
  - Settings クラスを提供し、アプリケーション設定（J-Quants / kabuステーション / Slack / DB パス / 環境モード / ログレベル等）を環境変数から取得・バリデート。
    - 必須構成項目未設定時は ValueError を送出。
    - KABUSYS_ENV と LOG_LEVEL の値検証を実装（許容値は定義済みの集合に制限）。
    - Path 型での duckdb/sqlite パス取得をサポート。

- AI（自然言語処理）機能（src/kabusys/ai）
  - ニュースセンチメントスコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini）の JSON Mode でバッチ評価。
    - 時間ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で提供。
    - チャンク処理（1回の API 呼び出しあたり最大 20 銘柄）、1銘柄あたり記事数・文字数の上限でトークン肥大化を回避。
    - レート制限 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装。
    - API レスポンスの厳密なバリデーション（JSON 抽出・results リスト・code/score 検証・数値チェック）と ±1.0 でのクリッピング。
    - スコア取得済み銘柄のみ ai_scores テーブルへ冪等的に置換（DELETE → INSERT）。部分失敗時に既存データを保護する設計。
    - テスト容易性のため OpenAI 呼び出しを差し替え可能（内部 _call_openai_api をパッチ可能に実装）。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を組み合わせて日次で市場レジーム（bull/neutral/bear）を算出。
    - マクロニュースは raw_news からマクロキーワードでフィルタし、OpenAI（gpt-4o-mini）で JSON レスポンスを期待してセンチメントを取得。
    - LLM 呼び出しのリトライ・フェイルセーフ実装（API 失敗時は macro_sentiment=0 にフォールバック）。
    - レジーム計算結果を market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。DB 書き込み失敗時は ROLLBACK を行い例外を伝播。
    - ルックアヘッドバイアス防止のため、target_date 未満のデータのみ参照する等の注意を実装。

- データ基盤ユーティリティ（src/kabusys/data）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルに基づく営業日判定ロジックを提供:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を実装。
    - DB にカレンダー情報がない場合は曜日ベース（土日を休場）でフォールバック。
    - next/prev/get_trading_days は DB 登録値を優先し未登録日は曜日フォールバックで一貫した挙動を返す。
    - calendar_update_job を実装し、J-Quants API から差分取得して market_calendar を冪等的に更新（バックフィル／健全性チェックを含む）。
  - ETL パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラスを実装し、ETL 実行結果と品質問題・エラーの集約をサポート。
    - 差分取得、バックフィル、品質チェック（kabusys.data.quality）といった設計方針を反映したヘルパーを実装。
    - テーブル存在チェックや最大日付取得などのユーティリティを提供。

- 研究用モジュール（src/kabusys/research）
  - factor_research.py:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離などのモメンタム指標を計算（prices_daily に依存）。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比などを計算。
    - calc_value: raw_financials から EPS/ROE を取り出し PER/ROE を計算（target_date 以前の最新財務データを利用）。
    - 計算は DuckDB SQL を利用して高速に実行；不足データ時は None を返す。
  - feature_exploration.py:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）に対する将来リターンをまとめて取得。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。十分な観測がない場合は None を返す。
    - rank: 同順位は平均ランクを割り当てるランク化ユーティリティ（丸め対策あり）。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を計算するユーティリティ。
  - data.stats の zscore_normalize を re-export（src/kabusys/research/__init__.py）。

- DuckDB を中心にした DB 操作方針
  - DuckDB 接続を受け取る設計で、Look-ahead バイアス防止とデータ不整合への堅牢性を重視。
  - executemany の空リストバインド等の DuckDB 特性への互換性考慮を反映。

Security
- OpenAI API キーは api_key 引数もしくは環境変数 OPENAI_API_KEY から解決。未設定時は明示的にエラーを返すことでキー漏洩などの誤使用を抑制。
- .env ローダーは OS 環境変数を protected として保護する仕組みを導入。

Deprecated
- （なし）

Removed
- （なし）

Fixed
- （初版のため該当なし）

Notes
- 多くの場所で「ルックアヘッドバイアス防止」の設計が反映されています（datetime.today()/date.today() を直接参照しない、DB クエリに排他条件を付与する等）。
- OpenAI 呼び出しや外部 API の失敗に対してフェイルセーフ（スコアを 0 に置換、部分的に処理をスキップ）する方針を採用しており、運用中の全体停止リスクを低減しています。
- テスト容易性のため、OpenAI 呼び出し等の内部関数はパッチ可能な実装になっています（unittest.mock.patch で差し替え可）。

今後の予定（例）
- strategy / execution / monitoring の具体実装拡充
- 品質チェックモジュールの拡張と ETL の自動スケジューリングサポート
- モデルやプロンプトの改善、スコアリング精度向上のためのチューニング

---