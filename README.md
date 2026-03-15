# KabuSys

KabuSys は日本株向けの自動売買システムのベースとなる Python パッケージの骨組みです。本リポジトリは最小限のパッケージ構成（データ取得、戦略、売買実行、モニタリング）を提供しており、実際のロジックや外部接続を実装して拡張することを想定しています。

---

## プロジェクト概要

- パッケージ名: `kabusys`
- 目的: 日本株の自動売買を行うためのモジュール分割された基盤を提供する
- 現状: パッケージ構造と名前空間のみ定義（バージョン 0.1.0）
- 主なモジュール:
  - `kabusys.data` : 市場データ取得・加工用
  - `kabusys.strategy` : 売買戦略（シグナル生成）
  - `kabusys.execution` : 注文送信・約定管理
  - `kabusys.monitoring` : ロギング・監視・ダッシュボード

---

## 機能一覧

現状（骨組み段階）での機能:

- パッケージの名前空間とバージョン管理（`kabusys.__version__`）
- モジュール分割（`data`, `strategy`, `execution`, `monitoring`）
- 将来的な実装のための拡張ポイントを明確化

今後の追加想定機能（例）:

- 証券会社 API（kabuステーション等）との連携
- 時系列データの取得・保存・バックテスト機能
- 複数戦略の管理、ポジション管理とリスク制御
- Web ダッシュボードやアラート機能

---

## 要求環境

- Python 3.8 以上推奨
- 必要なサードパーティライブラリは未定義（実装に応じて `requirements.txt` を作成してください）

---

## セットアップ手順

以下は開発環境でこのリポジトリを利用するための一般的な手順です。

1. リポジトリをクローンする
   ```
   git clone <repository-url>
   cd <repository-directory>
   ```

2. 仮想環境を作成・有効化（推奨）
   - macOS / Linux:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 依存関係をインストール
   - 依存ファイルが無い場合、特に何も不要です。将来的に `requirements.txt` や `pyproject.toml` を追加してください。
   - パッケージを開発モードでインストールする場合（`setup.py` または `pyproject.toml` があることが前提）:
     ```
     pip install -e .
     ```

4. 代替（ローカルソースを直接参照する）方法
   - パッケージのルートを PYTHONPATH に追加して実行:
     ```
     export PYTHONPATH=$(pwd)/src:$PYTHONPATH   # macOS / Linux
     set PYTHONPATH=%cd%\src;%PYTHONPATH%       # Windows (cmd)
     ```
   - これによりローカルの `src/kabusys` をインポートできます。

---

## 使い方

現状は名前空間のみ定義されているため、基本的なインポートとバージョン確認の例を示します。

Python REPL やスクリプト内で:
```python
import kabusys

print(kabusys.__version__)  # "0.1.0"
```

モジュール構造に応じた利用イメージ:
```python
from kabusys import data, strategy, execution, monitoring

# data: 市場データ取得・整形
# strategy: シグナル生成（例: エントリー/イグジット判定）
# execution: 注文送信・注文管理
# monitoring: ログ収集や監視・アラート

# 実装例（擬似コード）
# df = data.fetch_ohlcv("7203.T", start="2022-01-01", end="2022-12-31")
# signals = strategy.generate_signals(df)
# execution.send_order(signals)
# monitoring.report_status()
```

各モジュールは現段階では空のパッケージです。実際のロジックはそれぞれのサブパッケージ内に実装してください。

---

## ディレクトリ構成

リポジトリの主要ファイル配置（現状）:
```
.
├─ src/
│  └─ kabusys/
│     ├─ __init__.py          # パッケージメタ情報（バージョン、__all__）
│     ├─ data/
│     │  └─ __init__.py       # データ取得用モジュール（未実装）
│     ├─ strategy/
│     │  └─ __init__.py       # 戦略ロジック用モジュール（未実装）
│     ├─ execution/
│     │  └─ __init__.py       # 注文実行用モジュール（未実装）
│     └─ monitoring/
│        └─ __init__.py       # 監視・ロギング用モジュール（未実装）
└─ README.md                  # （このファイル）
```

---

## 開発・拡張のヒント

- 各サブパッケージに責務に沿ったクラス・関数を追加してください（例: data.fetch_*, strategy.BaseStrategy, execution.OrderManager, monitoring.Logger）。
- 外部 API を扱う場合は認証情報を直接リポジトリに置かず、環境変数や設定ファイル（.env）で管理してください。
- 単体テスト（pytest 等）や型チェック（mypy）を導入すると保守性が向上します。

---

必要であれば、README に以下を追加します（ご希望を教えてください）:
- 具体的な実装例（kabuステーション連携、注文フロー）
- CI/CD、パッケージ公開手順
- テスト・リンティングのセットアップ方法

以上。