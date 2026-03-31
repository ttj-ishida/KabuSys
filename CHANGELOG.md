# Changelog

すべての注記は Keep a Changelog の形式に準拠します。  
このファイルは、リポジトリ内のコードの内容から推測して生成した初期リリース向けの変更履歴（日本語）です。

フォーマット: [日付] 形式は YYYY-MM-DD

## [Unreleased]
- なし

## [0.1.0] - 2026-03-31
初回公開リリース。主要機能と設計方針を実装。

### Added
- パッケージ基盤
  - パッケージ名 kabusys とバージョン情報 (`__version__ = "0.1.0"`) を追加。
  - package-level `__all__` に data, strategy, execution, monitoring を公開対象として定義（将来的なモジュール拡張を想定）。

- 設定・環境変数管理（kabusys.config）
  - .env ファイルおよび環境変数の自動読み込み機能を実装。プロジェクトルートは `.git` または `pyproject.toml` を基準に探索するため、CWD に依存しない設計。
  - `.env` と `.env.local` の読み込み優先度を実装（OS環境変数 > .env.local > .env）。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動ロードを無効化可能。
  - .env 行パーサーの強化:
    - `export KEY=val` 形式対応。
    - シングル/ダブルクォート内でのバックスラッシュエスケープ処理対応。
    - インラインコメント処理（クォート外での `#` の扱い）対応。
  - Settings クラスを追加し、アプリケーション設定プロパティを提供（J-Quants refresh token、kabu API 設定、Slack トークン/チャンネル、DB パス、環境・ログレベル判定等）。
  - 環境値検証（KABUSYS_ENV / LOG_LEVEL の許容値チェック）と利便性メソッド（is_live / is_paper / is_dev）を実装。

- AI モジュール（kabusys.ai）
  - news_nlp モジュール（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄ごとのセンチメント（ai_score）を取得して ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティ `calc_news_window` を提供。
    - 1銘柄あたり最大記事数・文字数トリム、チャンクバッチ（最大 20 銘柄 / コール）を実装。
    - API 呼び出し時のリトライ（429 / ネットワーク断 / タイムアウト / 5xx）と指数バックオフを実装。フェイルセーフとして API 失敗時は該当チャンクをスキップし処理継続。
    - レスポンスの厳密なバリデーションと数値クリップ（±1.0）。部分失敗に備え、ai_scores テーブルへの書き込みは対象コードの DELETE → INSERT により既存データを保護。
    - テスト用に _call_openai_api を patch で差し替え可能な設計。
    - パブリック API: `score_news(conn, target_date, api_key=None)`。

  - regime_detector モジュール（kabusys.ai.regime_detector）
    - ETF 1321（Nikkei 225 連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）をスコアリング。
    - MA 計算時にルックアヘッドバイアスを防ぐため target_date 未満のデータのみを使用。データ不足時は中立（1.0）にフォールバック。
    - マクロニュースは news_nlp のウィンドウ計算ユーティリティを利用して抽出。LLM 呼び出しは独立実装でモジュール結合を低減。
    - OpenAI 呼び出しでのリトライ・エラー分類（5xx 再試行、非5xx はフォールバック）と JSON パースの堅牢化を実装。API エラー時は macro_sentiment=0.0 をフェイルセーフとして採用。
    - 結果は `market_regime` テーブルへ冪等（BEGIN / DELETE / INSERT / COMMIT）で書き込み。
    - パブリック API: `score_regime(conn, target_date, api_key=None)`。

- データモジュール（kabusys.data）
  - calendar_management
    - JPX カレンダー（market_calendar）を管理するユーティリティ（営業日判定、next/prev_trading_day、get_trading_days、is_sq_day）を実装。
    - DB 登録有無に応じた振る舞い（DB 値優先、未登録日は曜日ベースでフォールバック）を一貫して実装。
    - 夜間バッチ更新ジョブ `calendar_update_job(conn, lookahead_days=...)` を実装し、J-Quants API から差分取得 → 保存 → バックフィル（直近 N 日の再取得）を行う設計。健全性チェック（将来日付の異常検出）を追加。
    - market_calendar の存在チェックや NULL 値検出時の警告ログ出力など堅牢化。

  - ETL パイプライン（kabusys.data.pipeline + etl エクスポート）
    - ETL の結果を格納するデータクラス `ETLResult` を実装。取得件数、保存件数、品質チェック結果、エラーメッセージ一覧などを含む。
    - パイプラインユーティリティは差分更新、バックフィル、および品質チェックの設計方針に準拠（quality モジュール連携を想定）。
    - DuckDB のテーブル存在チェック、テーブル最大日付取得ユーティリティを実装。

- リサーチ / ファクター群（kabusys.research）
  - factor_research
    - モメンタム（1M/3M/6M）、200日移動平均乖離、ATR（20日）、平均売買代金、出来高比率、PER/ROE（raw_financials から）などの定量ファクター算出関数を実装:
      - `calc_momentum(conn, target_date)`：1m/3m/6m リターンと ma200_dev。
      - `calc_volatility(conn, target_date)`：atr_20, atr_pct, avg_turnover, volume_ratio。
      - `calc_value(conn, target_date)`：per, roe（財務データの最新レコードを参照）。
    - DuckDB のウィンドウ関数や LAG/AVG を活用し、データ不足時の None フォールバックを実装。

  - feature_exploration
    - 将来リターン計算 `calc_forward_returns(conn, target_date, horizons=None)`（デフォルト [1,5,21]）。
    - Information Coefficient（Spearman の ρ）計算 `calc_ic(...)`（ランク変換と欠損除外を含む）。
    - ランク変換ユーティリティ `rank(values)`（同順位は平均ランク）。
    - ファクター統計サマリー `factor_summary(records, columns)`（count, mean, std, min, max, median）を実装。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。

- テスト/運用配慮
  - OpenAI 呼び出し箇所に対してテスト時に差し替え可能な内部関数設計（unittest.mock.patch を利用）を導入。
  - DuckDB 0.10 系の挙動（executemany に空リスト不可）に対する対処（空チェック）を実装。
  - ルックアヘッドバイアス防止のため各処理で datetime.today() / date.today() の直接参照を避け、target_date ベースで処理する方針を徹底。

### Changed
- 初回リリースのため該当なし（将来のリリースで記載予定）。

### Fixed
- 初回リリースのため該当なし。

### Security
- 初回リリースのため該当なし。

### Deprecated
- なし

### Removed
- なし

---

注記（設計および実装に関する重要ポイント）
- ほとんどの外部 API 呼び出し（OpenAI, J-Quants）は冗長性（リトライ・バックオフ）とフェイルセーフ（スコア 0 相当やスキップ）を備えた設計になっており、部分的な外部障害が全体処理を停止させないようになっています。
- DB 書き込みは冪等性を重視（DELETE→INSERT の明示的置換や ON CONFLICT 想定）しており、部分失敗時のデータ保護（既存データを不用意に消さない）を心がけています。
- DuckDB をデータ操作の中心に据え、SQL + Python のハイブリッド実装でパフォーマンスと可読性のバランスを取っています。

以上。必要であれば、日付や追加のリリースノート（既知の制約や TODO、今後の計画）を追記します。