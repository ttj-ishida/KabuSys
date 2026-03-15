# KabuSys

KabuSys は日本株向けの自動売買システムの骨組み（スケルトン）です。パッケージは将来的にデータ取得、売買戦略、発注実行、監視／ログの各コンポーネントを分離して実装できるように構成されています。

バージョン: 0.1.0

---

## プロジェクト概要

このリポジトリは、自動売買システムを構築するための基盤パッケージです。現状はパッケージ構造と名前空間だけを含む最小実装で、各機能（data, strategy, execution, monitoring）は個別に実装して拡張できるようになっています。

目的：
- 日本株の自動売買システムをモジュール化して開発しやすくする
- 戦略ロジックと発注ロジックを分離してテストしやすい構造にする
- 監視（ログ／メトリクス）を独立して実装できるようにする

---

## 機能一覧（予定・設計上の分割）

現状はスケルトンですが、以下の機能を想定して設計しています：

- data: 市場データの取得（板情報、約定、ローソク足など）・前処理
- strategy: 売買戦略の定義・シグナル生成
- execution: 証券会社 API などを用いた発注・約定管理・注文キャンセル
- monitoring: ログ出力、取引履歴の保存、アラートやメトリクスの収集

各サブパッケージは将来的に独立して実装・テスト可能です。

---

## 動作環境・前提

- Python 3.8+
- （任意）仮想環境の使用を推奨
- 実際に市場データや発注を行う場合は、証券会社の API キーや通信設定が必要になります（例：kabuステーション、kabu.com API など）。それらの設定・依存パッケージは実装時に追加してください。

---

## セットアップ手順

このリポジトリはソースが `src/` に配置された構成です。開発環境の基本手順は以下の通りです。

1. リポジトリをクローン
   ```
   git clone <repository-url>
   cd <repository-directory>
   ```

2. 仮想環境の作成（推奨）
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

3. 依存関係のインストール
   - 依存ファイル（requirements.txt や pyproject.toml）がない場合は、必要に応じて作成してください。
   - 開発中はパッケージを editable インストールしておくと便利です（プロジェクトに packaging 設定がある場合）：
     ```
     pip install -e .
     ```
   - packaging ファイルが未設定の場合、実行時に Python のパスへ `src` を追加して使います：
     - UNIX 系:
       ```
       export PYTHONPATH=$(pwd)/src:$PYTHONPATH
       ```
     - Windows:
       ```
       set PYTHONPATH=%CD%\src;%PYTHONPATH%
       ```

4. 動作確認（簡易）
   - Python REPL またはスクリプトでバージョンを確認できます：
     ```python
     import kabusys
     print(kabusys.__version__)  # => "0.1.0"
     ```

---

## 使い方（例 / 開発時の操作）

現状はモジュールの雛形のみですが、以下は開発や利用のサンプルワークフロー例です。

1. データ取得コンポーネントの実装例（src/kabusys/data/...）
   - 例: MarketDataFetcher クラスを作り、板情報やローソク足を返す API を実装する。

2. 戦略コンポーネントの実装例（src/kabusys/strategy/...）
   - 例: StrategyBase クラスを定義し、`on_market_data()` でシグナルを返すメソッドを実装する。

3. 発注コンポーネントの実装例（src/kabusys/execution/...）
   - 例: ExecutionClient を作成し、注文送信、注文状況のポーリング、キャンセル処理などを実装する。

4. 監視コンポーネントの実装例（src/kabusys/monitoring/...）
   - 例: Logger, MetricsCollector, AlertManager を実装し、取引ログや異常検知を行う。

簡単なインポート例：
```python
# src がパスに含まれている前提
import kabusys
from kabusys import data, strategy, execution, monitoring

print("KabuSys version:", kabusys.__version__)
# 各サブパッケージに実装したクラスを使って処理を組み立てる
```

テスト実行や CI を導入する場合は、pytest や flake8 等を追加してください。

---

## ディレクトリ構成

このリポジトリの主要ファイル・ディレクトリ構成（現状）:

- src/
  - kabusys/
    - __init__.py        # パッケージメタ情報（バージョンなど）
    - data/
      - __init__.py      # データ取得関連の実装を配置
    - strategy/
      - __init__.py      # 売買戦略の実装を配置
    - execution/
      - __init__.py      # 発注・注文管理の実装を配置
    - monitoring/
      - __init__.py      # 監視・ログ・メトリクスの実装を配置

README や他のドキュメント、テスト、設定ファイル等はリポジトリルートに配置してください（例: requirements.txt, pyproject.toml, tests/）。

ツリー（簡易）
```
.
├─ src/
│  └─ kabusys/
│     ├─ __init__.py
│     ├─ data/
│     │  └─ __init__.py
│     ├─ strategy/
│     │  └─ __init__.py
│     ├─ execution/
│     │  └─ __init__.py
│     └─ monitoring/
│        └─ __init__.py
└─ README.md
```

---

## 開発ガイドライン（提案）

- 小さな単位 (data / strategy / execution / monitoring) ごとにモジュール／クラスを分けて実装する
- インターフェース（抽象クラス）を定義し、ユニットテストしやすくする
- 発注実行部はサンドボックス環境やモックで十分にテストする（実際の注文送信は慎重に）
- 設定や API キーは環境変数や設定ファイル（例: TOML / YAML）で管理する
- ロギングとメトリクスは必須（障害時の調査・監視のため）

---

## 貢献方法

1. Issue を作成して機能追加やバグを提案してください
2. Fork -> ブランチ作成 -> Pull Request を送ってください
3. コーディング規約、テストを可能な限り同梱してください

---

## ライセンス

このリポジトリにライセンスファイルが含まれていない場合、利用方法や配布条件についてはリポジトリ所有者に確認してください。

---

この README は現状の最小構成（パッケージ骨組み）に基づく説明です。具体的な外部 API や依存パッケージ、設定手順は、各コンポーネントを実装する際に追加してください。必要であれば、実装例テンプレートや CI 設定の雛形も提供します。